package org.decisiongator;

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

@EnabledIfSystemProperty(named = "decisiongator.bundle", matches = ".+")
class DecisionGatorIntegrationTest {
    private static final String CONTENT = "Please cancel my subscription before the next renewal.";
    private static final String QUESTION = "Is the customer asking to cancel their subscription?";
    // Release goldens remain the default; alternate bundles supply independent native results.
    private static final double EXPECTED = Double.parseDouble(
            System.getProperty("decisiongator.expectedProbability", "0.9969299857604682"));
    private static final double EXPECTED_UNICODE = Double.parseDouble(
            System.getProperty("decisiongator.expectedUnicodeProbability", "0.994877095049259"));
    // The quantized 0.4.1 model rounds slightly differently on each processor; these confident cases stay within 0.005.
    private static final double GOLDEN_TOLERANCE = 5e-3;
    private static DecisionGator model;

    @BeforeAll
    static void open() {
        model = DecisionGator.load(Path.of(System.getProperty("decisiongator.bundle")));
    }

    @AfterAll
    static void close() {
        if (model != null) model.close();
    }

    @Test
    void repeatedPredictionAndProbabilityRange() {
        double actual = model.evaluate(CONTENT, QUESTION);
        assertTrue(Double.isFinite(actual) && actual >= 0 && actual <= 1);
        assertEquals(EXPECTED, actual, GOLDEN_TOLERANCE);
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
        assertEquals(EXPECTED_UNICODE, actual, GOLDEN_TOLERANCE);
        assertEquals(actual, model.evaluate(content, question, criteria), 1e-7);
    }

    @Test
    void metadataIsBundleManifest() throws Exception {
        String metadata = model.metadataJson();
        String manifest = Files.readString(Path.of(System.getProperty("decisiongator.bundle"), "manifest.json"));
        // Native metadata preserves the loaded manifest, including formatting.
        assertEquals(manifest, metadata);
    }

    @Test
    void invalidTextAndNativeErrorsRemainErrors() {
        double beforeErrors = model.evaluate(CONTENT, QUESTION);
        for (String invalid : new String[] {null, "", " \t\n", "\ud800", "\udfff", "a\ud800b"}) {
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> model.evaluate(invalid, QUESTION)).statusCode());
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> model.evaluate(CONTENT, invalid)).statusCode());
        }
        DecisionGatorException tooLong = assertThrows(DecisionGatorException.class,
                () -> model.evaluate("x".repeat(1_048_577), QUESTION));
        assertEquals(7, tooLong.statusCode());
        assertFalse(tooLong.getMessage().isBlank());
        assertEquals(7, assertThrows(DecisionGatorException.class,
                () -> model.evaluate("word ".repeat(600), QUESTION)).statusCode());
        assertEquals(beforeErrors, model.evaluate(CONTENT, QUESTION), 1e-7);
    }

    @Test
    void repeatedCloseAndPostCloseAccess() {
        DecisionGator disposable = DecisionGator.load(Path.of(System.getProperty("decisiongator.bundle")));
        disposable.close();
        disposable.close();
        assertEquals(1, assertThrows(DecisionGatorException.class,
                () -> disposable.evaluate(CONTENT, QUESTION)).statusCode());
        assertThrows(DecisionGatorException.class, disposable::metadataJson);
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
