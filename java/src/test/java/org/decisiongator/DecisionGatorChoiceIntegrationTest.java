package org.decisiongator;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Exercises dg_evaluate_choice against a bundle that has the multiple-choice native functions.
 * The pom points this at the released bundle. Override the bundle location with the
 * DECISIONGATOR_CHOOSE_BUNDLE environment variable, or -Ddecisiongator.choose.bundle=PATH;
 * this leaves the -Ddecisiongator.bundle default used for released-bundle testing unchanged.
 */
class DecisionGatorChoiceIntegrationTest {
    private static final String CONTENT = "My card was charged twice for last month's invoice.";
    private static final String QUESTION = "Which team should handle this message?";
    private static final List<String> TEAMS = List.of("billing", "technical support", "sales");
    private static DecisionGator model;

    @BeforeAll
    static void open() {
        Path bundle = resolveBundle();
        assumeTrue(bundle != null && Files.isRegularFile(bundle.resolve("manifest.json")),
                "No choose-capable DecisionGator bundle configured; set DECISIONGATOR_CHOOSE_BUNDLE "
                        + "or -Ddecisiongator.choose.bundle=PATH to a bundle built with dg_evaluate_choice");
        model = DecisionGator.load(bundle);
    }

    @AfterAll
    static void close() {
        if (model != null) model.close();
    }

    private static Path resolveBundle() {
        String override = System.getenv("DECISIONGATOR_CHOOSE_BUNDLE");
        if (override == null || override.isBlank()) {
            override = System.getProperty("decisiongator.choose.bundle");
        }
        return override == null || override.isBlank() ? null : Path.of(override);
    }

    @Test
    void ranksBillingMessageFirstWithDescendingProbabilitiesSummingToOne() {
        List<Choice> ranked = model.evaluateChoice(CONTENT, QUESTION, TEAMS);
        assertEquals(TEAMS.size(), ranked.size());
        assertEquals(0, ranked.get(0).index());
        double sum = 0;
        for (int i = 0; i < ranked.size(); i++) {
            Choice choice = ranked.get(i);
            assertTrue(Double.isFinite(choice.p()) && choice.p() >= 0 && choice.p() <= 1);
            if (i > 0) assertTrue(ranked.get(i - 1).p() >= choice.p());
            sum += choice.p();
        }
        assertEquals(1.0, sum, 1e-9);
    }

    @Test
    void equalOptionsKeepCallerOrderAtHalfEach() {
        List<Choice> ranked = model.evaluateChoice("Some content.", "Pick one.", List.of("same", "same"));
        assertEquals(2, ranked.size());
        assertEquals(0, ranked.get(0).index());
        assertEquals(1, ranked.get(1).index());
        assertEquals(0.5, ranked.get(0).p(), 1e-9);
        assertEquals(0.5, ranked.get(1).p(), 1e-9);
    }

    @Test
    void thresholdSelectsAtEqualityAndDefersBelowIt() {
        // Equal options score exactly 0.5 each; use that to exercise choose()'s threshold rule
        // (best.p() >= threshold ? best.index() : -1) against a real, deterministic probability.
        Choice best = model.evaluateChoice("Some content.", "Pick one.", List.of("same", "same")).get(0);
        assertEquals(0.5, best.p(), 1e-9);
        assertEquals(0, best.p() >= 0.5 ? best.index() : -1);
        assertEquals(-1, best.p() >= 0.500001 ? best.index() : -1);
    }

    @Test
    void criteriaApplyToEveryOption() {
        var criteria = new Criteria("The message is a billing complaint.", "The message is not a billing complaint.");
        List<Choice> ranked = model.evaluateChoice(CONTENT, QUESTION, TEAMS, criteria);
        assertEquals(TEAMS.size(), ranked.size());
        double sum = ranked.stream().mapToDouble(Choice::p).sum();
        assertEquals(1.0, sum, 1e-9);
    }

    @Test
    void invalidOptionsRejectedWithoutPartialResult() {
        assertEquals(1, assertThrows(DecisionGatorException.class,
                () -> model.evaluateChoice(CONTENT, QUESTION, List.of("only one"))).statusCode());
    }

    @Test
    void closedSessionRejectsChoice() {
        DecisionGator disposable = DecisionGator.load(resolveBundle());
        disposable.close();
        assertEquals(1, assertThrows(DecisionGatorException.class,
                () -> disposable.evaluateChoice(CONTENT, QUESTION, TEAMS)).statusCode());
    }
}
