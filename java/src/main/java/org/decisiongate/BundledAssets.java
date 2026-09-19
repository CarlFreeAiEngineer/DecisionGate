package org.decisiongate;

import java.io.IOException;
import java.io.InputStream;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Locale;

/** Extracts only assets already on the application's classpath. Never downloads. */
final class BundledAssets {
    private BundledAssets() { }

    static synchronized DecisionGate load(Path cacheDirectory) {
        String platform = platform();
        String prefix = "META-INF/decisiongate/" + platform + "/";
        try {
            byte[] index;
            try (InputStream stream = BundledAssets.class.getClassLoader().getResourceAsStream(prefix + "bundle.index")) {
                if (stream == null) {
                    throw new IllegalStateException("No DecisionGate bundle for " + platform
                        + " on the classpath. Add the matching native classifier dependency, or use DecisionGate.load(Path).");
                }
                index = stream.readAllBytes();
            }
            String identity = HexFormat.of().formatHex(sha256().digest(index));
            Path directory = cacheDirectory.toAbsolutePath().normalize().resolve(identity).resolve(platform);
            Files.createDirectories(directory);
            try (FileChannel channel = FileChannel.open(directory.resolve(".extract.lock"),
                    StandardOpenOption.CREATE, StandardOpenOption.WRITE);
                 FileLock ignored = channel.lock()) {
                for (String line : new String(index, StandardCharsets.UTF_8).split("\\R")) {
                    if (line.isBlank()) continue;
                    String[] fields = line.split("\\t", 2);
                    if (fields.length != 2 || !fields[0].matches("[0-9a-f]{64}")) {
                        throw new IOException("Invalid bundled asset index");
                    }
                    String relative = fields[1];
                    Path target = directory.resolve(relative).normalize();
                    if (relative.contains("\\") || Path.of(relative).isAbsolute()
                            || !target.startsWith(directory) || target.equals(directory)) {
                        throw new IOException("Invalid bundled asset path");
                    }
                    if (Files.isRegularFile(target, LinkOption.NOFOLLOW_LINKS)
                            && hash(target).equals(fields[0])) continue;
                    Files.createDirectories(target.getParent());
                    Path staged = Files.createTempFile(target.getParent(), ".decisiongate-", ".part");
                    try {
                        try (InputStream resource = BundledAssets.class.getClassLoader().getResourceAsStream(prefix + relative)) {
                            if (resource == null) throw new IOException("Missing bundled asset: " + relative);
                            Files.copy(resource, staged, StandardCopyOption.REPLACE_EXISTING);
                        }
                        if (!hash(staged).equals(fields[0])) throw new IOException("Bundled asset hash mismatch: " + relative);
                        Files.move(staged, target, StandardCopyOption.REPLACE_EXISTING);
                    } finally {
                        Files.deleteIfExists(staged);
                    }
                }
            }
            return DecisionGate.load(directory);
        } catch (IOException e) {
            throw new IllegalStateException("Could not prepare local DecisionGate bundle", e);
        }
    }

    private static String platform() {
        String os = System.getProperty("os.name").toLowerCase(Locale.ROOT);
        String arch = System.getProperty("os.arch").toLowerCase(Locale.ROOT);
        boolean x64 = arch.equals("amd64") || arch.equals("x86_64");
        if ((os.contains("mac") || os.contains("darwin")) && (arch.equals("aarch64") || arch.equals("arm64"))) return "macos-arm64";
        if (os.startsWith("windows") && x64) return "windows-x64";
        if (os.contains("linux") && x64) return "linux-x64";
        throw new UnsupportedOperationException("Unsupported DecisionGate platform: " + os + " / " + arch);
    }

    private static MessageDigest sha256() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException e) { throw new AssertionError(e); }
    }

    private static String hash(Path path) throws IOException {
        MessageDigest digest = sha256();
        try (InputStream input = Files.newInputStream(path)) {
            byte[] buffer = new byte[65536];
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        return HexFormat.of().formatHex(digest.digest());
    }
}
