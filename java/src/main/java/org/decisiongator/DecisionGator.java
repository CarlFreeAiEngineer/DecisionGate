package org.decisiongator;

import com.sun.jna.Memory;
import com.sun.jna.Native;
import com.sun.jna.Pointer;
import com.sun.jna.ptr.DoubleByReference;
import com.sun.jna.ptr.PointerByReference;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * An offline decision component backed by a native bundle. Close each session to release
 * its inference session. The native libraries remain loaded until process exit.
 * Use a stable application class loader; hot class-loader unloading is unsupported.
 * Finish inference before process exit, and do not call this API from exit hooks.
 */
public final class DecisionGator implements AutoCloseable {
    private static final Map<Path, NativeBindings> LIBRARIES = new HashMap<>();
    private final NativeBindings library;
    private Pointer handle;

    private DecisionGator(NativeBindings library, Pointer handle) {
        this.library = library;
        this.handle = handle;
    }

    /**
     * Extract and load platform assets packaged in the application class path.
     *
     * @return an open session owned by the caller
     * @throws DecisionGatorException if extraction or loading fails
     */
    public static DecisionGator loadBundled() {
        return loadBundled(Path.of(System.getProperty("user.home"), ".cache", "decisiongator"));
    }

    /**
     * Extract packaged platform assets into the supplied cache and load them.
     *
     * @param cacheDirectory directory used to cache extracted platform assets
     * @return an open session owned by the caller
     * @throws DecisionGatorException if extraction or loading fails
     */
    public static DecisionGator loadBundled(Path cacheDirectory) {
        return BundledAssets.load(cacheDirectory);
    }

    /**
     * Load the directory containing the manifest, model and platform libraries.
     *
     * @param bundle directory containing a complete native bundle
     * @return an open session owned by the caller
     * @throws DecisionGatorException if the bundle or platform is invalid, or loading fails
     */
    public static DecisionGator load(Path bundle) {
        if (bundle == null) {
            throw new DecisionGatorException(1, "bundle must not be null");
        }
        Path directory;
        Path binary;
        try {
            directory = bundle.toRealPath();
            if (!Files.isDirectory(directory)) {
                throw new IOException("Bundle is not a directory");
            }
            binary = directory.resolve(libraryName()).toRealPath();
        } catch (IOException e) {
            throw new DecisionGatorException(2, "Cannot read DecisionGator bundle: " + bundle, e);
        }
        NativeBindings library = library(binary);
        try (Utf8 path = new Utf8(directory.toString(), "bundle")) {
            PointerByReference model = new PointerByReference();
            check(library, library.dg_load(path.memory, path.length, model));
            if (model.getValue() == null) {
                throw new DecisionGatorException(6, "Native load returned a null session");
            }
            return new DecisionGator(library, model.getValue());
        }
    }

    private static synchronized NativeBindings library(Path binary) {
        NativeBindings existing = LIBRARIES.get(binary);
        if (existing != null) return existing;
        try {
            // A JVM-owned load keeps JNA disposal from unloading the component;
            // ONNX Runtime registers process-exit callbacks into this library.
            System.load(binary.toString());
            NativeBindings loaded = Native.load(binary.toString(), NativeBindings.class);
            LIBRARIES.put(binary, loaded);
            return loaded;
        } catch (LinkageError | SecurityException e) {
            throw new DecisionGatorException(2, "Cannot load native library: " + binary, e);
        }
    }

    static String libraryName() {
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        String arch = System.getProperty("os.arch", "").toLowerCase(Locale.ROOT);
        boolean arm64 = arch.equals("aarch64") || arch.equals("arm64");
        boolean x64 = arch.equals("amd64") || arch.equals("x86_64");
        if (os.startsWith("mac") && arm64) return "libdecisiongator.dylib";
        if (os.startsWith("windows") && x64) return "decisiongator.dll";
        if (os.equals("linux") && x64) return "libdecisiongator.so";
        throw new DecisionGatorException(3, "Unsupported platform: " + os + " / " + arch);
    }

    /**
     * Return the calibrated probability of a yes answer.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @return calibrated probability between zero and one, inclusive
     * @throws DecisionGatorException if the session is closed, input is invalid, or inference fails
     */
    public synchronized double evaluate(String content, String question) {
        return evaluate(content, question, null);
    }

    /**
     * Return a probability using optional explicit yes/no descriptions.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @param criteria explicit answer descriptions, or null to use the default descriptions
     * @return calibrated probability between zero and one, inclusive
     * @throws DecisionGatorException if the session is closed, input is invalid, or inference fails
     */
    public synchronized double evaluate(String content, String question, Criteria criteria) {
        requireOpen();
        try (Utf8 text = new Utf8(content, "content");
             Utf8 prompt = new Utf8(question, "question");
             Utf8 yes = criteria == null ? null : new Utf8(criteria.yes(), "criteria.yes");
             Utf8 no = criteria == null ? null : new Utf8(criteria.no(), "criteria.no")) {
            NativeBindings.NativeCriteria nativeCriteria = null;
            if (criteria != null) {
                nativeCriteria = new NativeBindings.NativeCriteria();
                nativeCriteria.yes = yes.memory;
                nativeCriteria.yesBytes = yes.length;
                nativeCriteria.no = no.memory;
                nativeCriteria.noBytes = no.length;
            }
            DoubleByReference probability = new DoubleByReference();
            check(library, library.dg_evaluate(handle, text.memory, text.length,
                    prompt.memory, prompt.length, nativeCriteria, probability));
            return probability.getValue();
        }
    }

    /**
     * Rank options best first for a question about the content.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @return every option ranked best first, as index/probability pairs summing to one
     * @throws DecisionGatorException if the session is closed, input is invalid, or inference fails
     */
    public synchronized List<Choice> evaluateChoice(String content, String question, List<String> options) {
        return evaluateChoice(content, question, options, null);
    }

    /**
     * Rank options best first using optional explicit yes/no descriptions.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @param criteria explicit answer descriptions applied to every option, or null for defaults
     * @return every option ranked best first, as index/probability pairs summing to one
     * @throws DecisionGatorException if the session is closed, input is invalid, or inference fails
     */
    public synchronized List<Choice> evaluateChoice(String content, String question, List<String> options,
            Criteria criteria) {
        requireOpen();
        Utf8.validateOptions(options);
        try (Utf8 text = new Utf8(content, "content");
             Utf8 prompt = new Utf8(question, "question");
             Utf8 yes = criteria == null ? null : new Utf8(criteria.yes(), "criteria.yes");
             Utf8 no = criteria == null ? null : new Utf8(criteria.no(), "criteria.no");
             OptionBuffers optionBuffers = new OptionBuffers(options)) {
            NativeBindings.NativeCriteria nativeCriteria = null;
            if (criteria != null) {
                nativeCriteria = new NativeBindings.NativeCriteria();
                nativeCriteria.yes = yes.memory;
                nativeCriteria.yesBytes = yes.length;
                nativeCriteria.no = no.memory;
                nativeCriteria.noBytes = no.length;
            }
            int count = options.size();
            int[] outIndex = new int[count];
            double[] outP = new double[count];
            check(library, library.dg_evaluate_choice(handle, text.memory, text.length,
                    prompt.memory, prompt.length, optionBuffers.pointers, optionBuffers.lengths,
                    new NativeBindings.SizeT(count), nativeCriteria, outIndex, outP));
            List<Choice> ranked = new ArrayList<>(count);
            for (int i = 0; i < count; i++) {
                ranked.add(new Choice(outIndex[i], outP[i]));
            }
            return List.copyOf(ranked);
        }
    }

    /** Borrowed native option arrays for one call: a pointer table and a matching length table. */
    private static final class OptionBuffers implements AutoCloseable {
        private final Utf8[] texts;
        final Memory pointers;
        final Memory lengths;

        OptionBuffers(List<String> options) {
            int count = options.size();
            texts = new Utf8[count];
            pointers = new Memory((long) count * Native.POINTER_SIZE);
            lengths = new Memory((long) count * Native.SIZE_T_SIZE);
            try {
                for (int i = 0; i < count; i++) {
                    texts[i] = new Utf8(options.get(i), "options[" + i + "]");
                    pointers.setPointer((long) i * Native.POINTER_SIZE, texts[i].memory);
                    writeSize(lengths, (long) i * Native.SIZE_T_SIZE, texts[i].length.longValue());
                }
            } catch (RuntimeException e) {
                close();
                throw e;
            }
        }

        @Override
        public void close() {
            pointers.close();
            lengths.close();
            for (Utf8 text : texts) {
                if (text != null) text.close();
            }
        }
    }

    private static void writeSize(Memory memory, long offset, long value) {
        if (Native.SIZE_T_SIZE == 8) memory.setLong(offset, value);
        else memory.setInt(offset, (int) value);
    }

    /**
     * Return the bundle manifest as JSON without adding a JSON-library dependency.
     *
     * @return the loaded bundle manifest in JSON format
     * @throws DecisionGatorException if the session is closed or metadata retrieval fails
     */
    public synchronized String metadataJson() {
        requireOpen();
        try (Memory required = new Memory(Native.SIZE_T_SIZE)) {
            check(library, library.dg_metadata(handle, null, new NativeBindings.SizeT(), required));
            long size = readSize(required);
            try (Memory buffer = new Memory(size)) {
                check(library, library.dg_metadata(handle, buffer, new NativeBindings.SizeT(size), required));
                return decode(buffer, size);
            }
        }
    }

    /** Release the session. Repeated calls are harmless. */
    @Override
    public synchronized void close() {
        if (handle != null) {
            library.dg_release(handle);
            handle = null;
        }
    }

    private void requireOpen() {
        if (handle == null) throw new DecisionGatorException(1, "DecisionGator session is closed");
    }

    private static long readSize(Memory required) {
        long size = Native.SIZE_T_SIZE == 8 ? required.getLong(0)
                : Integer.toUnsignedLong(required.getInt(0));
        if (size <= 0 || size > Integer.MAX_VALUE) {
            throw new DecisionGatorException(4, "Invalid native output buffer size: " + size);
        }
        return size;
    }

    private static String decode(Memory buffer, long size) {
        return new String(buffer.getByteArray(0, (int) size - 1), StandardCharsets.UTF_8);
    }

    private static void check(NativeBindings library, int status) {
        if (status == 0) return;
        String message = "Native operation failed (status " + status + ")";
        try (Memory required = new Memory(Native.SIZE_T_SIZE)) {
            if (library.dg_last_error(null, new NativeBindings.SizeT(), required) == 0) {
                long size = readSize(required);
                try (Memory buffer = new Memory(size)) {
                    if (library.dg_last_error(buffer, new NativeBindings.SizeT(size), required) == 0) {
                        String nativeMessage = decode(buffer, size);
                        if (!nativeMessage.isEmpty()) message = nativeMessage;
                    }
                }
            }
        } catch (DecisionGatorException ignored) {
            // Preserve the original native status if error retrieval is malformed.
        }
        throw new DecisionGatorException(status, message);
    }
}
