package org.decisiongate;

import com.sun.jna.Memory;
import java.nio.charset.StandardCharsets;
import java.util.List;

/** Owns the explicit UTF-8 byte buffer borrowed during a native call. */
final class Utf8 implements AutoCloseable {
    final Memory memory;
    final NativeBindings.SizeT length;

    Utf8(String value, String name) {
        validate(value, name);
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        length = new NativeBindings.SizeT(bytes.length);
        memory = new Memory(bytes.length + 1L);
        memory.write(0, bytes, 0, bytes.length);
        memory.setByte(bytes.length, (byte) 0);
    }

    static void validate(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new DecisionGateException(1, name + " must be nonempty");
        }
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (++i == value.length() || !Character.isLowSurrogate(value.charAt(i))) {
                    throw new DecisionGateException(1, name + " contains an unpaired UTF-16 surrogate");
                }
            } else if (Character.isLowSurrogate(c)) {
                throw new DecisionGateException(1, name + " contains an unpaired UTF-16 surrogate");
            }
        }
    }

    /** Validate the option list shape; each option's text is validated separately. */
    static void validateOptions(List<String> options) {
        if (options == null) {
            throw new DecisionGateException(1, "options must not be null");
        }
        if (options.size() < 2) {
            throw new DecisionGateException(1, "choose needs at least two options");
        }
        for (String option : options) {
            if (option == null || option.isBlank()) {
                throw new DecisionGateException(1, "options must be nonempty");
            }
        }
    }

    @Override
    public void close() {
        memory.close();
    }
}
