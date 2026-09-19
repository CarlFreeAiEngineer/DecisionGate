package org.decisiongate;

import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;

@EnabledIfSystemProperty(named = "decisiongate.bundle", matches = ".+")
class DecisionGateIntegrationTest {
    private static final String CONTENT = "Please cancel my subscription before the next renewal.";
    private static final String QUESTION = "Is the customer asking to cancel their subscription?";
    // Release goldens remain the default; alternate bundles supply independent native results.
    private static final double EXPECTED = Double.parseDouble(
            System.getProperty("decisiongate.expectedProbability", "0.9967822260684038"));
    private static final double EXPECTED_UNICODE = Double.parseDouble(
            System.getProperty("decisiongate.expectedUnicodeProbability", "0.9947915411986116"));
    private static DecisionGate model;

    @BeforeAll
    static void open() {
        model = DecisionGate.load(Path.of(System.getProperty("decisiongate.bundle")));
    }

    @AfterAll
    static void close() {
        if (model != null) model.close();
    }

    @Test
    void repeatedPredictionAndProbabilityRange() {
        double actual = model.evaluate(CONTENT, QUESTION);
        assertTrue(Double.isFinite(actual) && actual >= 0 && actual <= 1);
        assertEquals(EXPECTED, actual, 1e-6);
        assertEquals(actual, model.evaluate(CONTENT, QUESTION), 1e-7);
        assertEquals(actual, model.evaluate(CONTENT, QUESTION, null), 1e-7);
    }

    @Test
    void unicodeAndCriteriaProduceStableProbability() {
        String content = "Please cancel Renée’s café subscription. ☕";
        String question = "Is cancellation requested?";
        var criteria = new Criteria("An explicit request to cancel.", "No cancellation request.");
        double actual = model.evaluate(content, question, criteria);
        assertTrue(Double.isFinite(actual) && actual >= 0 && actual <= 1);
        assertEquals(EXPECTED_UNICODE, actual, 1e-6);
        assertEquals(actual, model.evaluate(content, question, criteria), 1e-7);
    }

    @Test
    void metadataIsBundleManifest() throws Exception {
        String metadata = model.metadataJson();
        String manifest = Files.readString(Path.of(System.getProperty("decisiongate.bundle"), "manifest.json"));
        // Native metadata preserves the loaded manifest, including formatting.
        assertEquals(manifest, metadata);
    }

    @Test
    void invalidTextAndNativeErrorsRemainErrors() {
        double beforeErrors = model.evaluate(CONTENT, QUESTION);
        for (String invalid : new String[] {null, "", " \t\n", "\ud800", "\udfff", "a\ud800b"}) {
            assertEquals(1, assertThrows(DecisionGateException.class,
                    () -> model.evaluate(invalid, QUESTION)).statusCode());
            assertEquals(1, assertThrows(DecisionGateException.class,
                    () -> model.evaluate(CONTENT, invalid)).statusCode());
        }
        DecisionGateException tooLong = assertThrows(DecisionGateException.class,
                () -> model.evaluate("x".repeat(1_048_577), QUESTION));
        assertEquals(7, tooLong.statusCode());
        assertFalse(tooLong.getMessage().isBlank());
        assertEquals(7, assertThrows(DecisionGateException.class,
                () -> model.evaluate("word ".repeat(600), QUESTION)).statusCode());
        assertEquals(beforeErrors, model.evaluate(CONTENT, QUESTION), 1e-7);
    }

    @Test
    void repeatedCloseAndPostCloseAccess() {
        DecisionGate disposable = DecisionGate.load(Path.of(System.getProperty("decisiongate.bundle")));
        disposable.close();
        disposable.close();
        assertEquals(1, assertThrows(DecisionGateException.class,
                () -> disposable.evaluate(CONTENT, QUESTION)).statusCode());
        assertThrows(DecisionGateException.class, disposable::metadataJson);
    }

    @Test
    void concurrentCallsOnOneHandle() throws Exception {
        double sequential = model.evaluate(CONTENT, QUESTION);
        var executor = Executors.newFixedThreadPool(3);
        try {
            List<Callable<Double>> calls = new ArrayList<>();
            for (int i = 0; i < 6; i++) calls.add(() -> model.evaluate(CONTENT, QUESTION));
            for (Future<Double> value : executor.invokeAll(calls)) {
                assertEquals(sequential, value.get(), 1e-7);
            }
        } finally {
            executor.shutdownNow();
        }
    }
}
