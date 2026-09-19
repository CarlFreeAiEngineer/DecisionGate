package org.decisiongate;

import static org.junit.jupiter.api.Assertions.*;

import com.sun.jna.Native;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class DecisionGateTest {
    @Test
    void validatesCriteria() {
        assertEquals("Yes", new Criteria("Yes", "No").yes());
        for (String invalid : new String[] {null, "", " \n\t", "\ud800", "\udfff", "a\ud800b"}) {
            assertEquals(1, assertThrows(DecisionGateException.class,
                    () -> new Criteria(invalid, "No")).statusCode());
            assertThrows(DecisionGateException.class, () -> new Criteria("Yes", invalid));
        }
        assertDoesNotThrow(() -> new Criteria("Café ☕ 😀", "不存在"));
    }

    @Test
    void explicitUtf8PreservesUnicodeAndEmbeddedNul() {
        String value = "Renée ☕ 😀\0end";
        byte[] expected = value.getBytes(StandardCharsets.UTF_8);
        try (Utf8 text = new Utf8(value, "text")) {
            assertEquals(expected.length, text.length.longValue());
            assertArrayEquals(expected, text.memory.getByteArray(0, expected.length));
            assertEquals(0, text.memory.getByte(expected.length));
        }
    }

    @Test
    void nativeSizesMatchHeader() {
        assertEquals(Native.SIZE_T_SIZE, Native.getNativeSize(NativeBindings.SizeT.class));
        assertEquals(2 * Native.POINTER_SIZE + 2 * Native.SIZE_T_SIZE,
                new NativeBindings.NativeCriteria().size());
    }

    @Test
    void missingBundleIsLoadError(@TempDir Path temporary) {
        assertEquals(2, assertThrows(DecisionGateException.class,
                () -> DecisionGate.load(temporary.resolve("missing"))).statusCode());
        assertEquals(2, assertThrows(DecisionGateException.class,
                () -> DecisionGate.load(temporary)).statusCode());
        assertEquals(1, assertThrows(DecisionGateException.class,
                () -> DecisionGate.load(null)).statusCode());
    }

    @Test
    void choiceRecordExposesIndexAndProbability() {
        Choice choice = new Choice(2, 0.75);
        assertEquals(2, choice.index());
        assertEquals(0.75, choice.p());
    }

    @Test
    void validatesOptionShape() {
        assertDoesNotThrow(() -> Utf8.validateOptions(List.of("billing", "sales")));
        assertEquals(1, assertThrows(DecisionGateException.class,
                () -> Utf8.validateOptions(null)).statusCode());
        assertEquals(1, assertThrows(DecisionGateException.class,
                () -> Utf8.validateOptions(List.of())).statusCode());
        assertEquals(1, assertThrows(DecisionGateException.class,
                () -> Utf8.validateOptions(List.of("only one"))).statusCode());
        assertEquals(1, assertThrows(DecisionGateException.class,
                () -> Utf8.validateOptions(Arrays.asList("billing", null))).statusCode());
        assertEquals(1, assertThrows(DecisionGateException.class,
                () -> Utf8.validateOptions(List.of("billing", " \t\n"))).statusCode());
    }
}
