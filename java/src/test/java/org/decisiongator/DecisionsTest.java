package org.decisiongator;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class DecisionsTest {
    @Test
    void invalidTextIsRejectedBeforeLoadingAssets() {
        for (String invalid : new String[] {null, "", " \n", "\ud800", "\udfff"}) {
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.isYesP(invalid, "Is cancellation requested?")).statusCode());
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.isYes(invalid, "Is cancellation requested?")).statusCode());
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.isYesP("Cancel my subscription.", invalid,
                            new Criteria("A cancellation request.", "No cancellation request."))).statusCode());
        }
    }

    private static final List<String> TEAMS = List.of("billing", "technical support", "sales");
    private static final String CONTENT = "My card was charged twice for last month's invoice.";
    private static final String QUESTION = "Which team should handle this message?";

    @Test
    void invalidTextIsRejectedBeforeLoadingAssetsForChoose() {
        for (String invalid : new String[] {null, "", " \n", "\ud800", "\udfff"}) {
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.chooseP(invalid, QUESTION, TEAMS)).statusCode());
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.choose(invalid, QUESTION, TEAMS)).statusCode());
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.chooseP(CONTENT, invalid, TEAMS)).statusCode());
        }
    }

    @Test
    void invalidOptionsAreRejectedBeforeLoadingAssets() {
        for (List<String> invalid : new List[] {null, List.of(), List.of("only one"),
                Arrays.asList("billing", null), List.of("billing", " \t\n")}) {
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.chooseP(CONTENT, QUESTION, invalid)).statusCode());
            assertEquals(1, assertThrows(DecisionGatorException.class,
                    () -> Decisions.choose(CONTENT, QUESTION, invalid)).statusCode());
        }
    }

    @Test
    void invalidThresholdsForChooseAreRejectedBeforeTextValidationOrLoading() {
        for (double threshold : new double[] {Double.NaN, Double.NEGATIVE_INFINITY,
                Double.POSITIVE_INFINITY, -Double.MIN_VALUE, Math.nextUp(1.0)}) {
            assertThrows(IllegalArgumentException.class,
                    () -> Decisions.choose(null, null, null, threshold));
            assertThrows(IllegalArgumentException.class,
                    () -> Decisions.choose(null, null, null, new Criteria("Yes", "No"), threshold));
        }
        for (double threshold : new double[] {0.0, -0.0, 0.5, 1.0}) {
            assertThrows(DecisionGatorException.class,
                    () -> Decisions.choose(null, null, null, threshold));
        }
    }

    @Test
    void invalidThresholdsAreRejectedBeforeTextValidationOrLoading() {
        for (double threshold : new double[] {Double.NaN, Double.NEGATIVE_INFINITY,
                Double.POSITIVE_INFINITY, -Double.MIN_VALUE, Math.nextUp(1.0)}) {
            assertThrows(IllegalArgumentException.class,
                    () -> Decisions.isYes(null, null, threshold));
            assertThrows(IllegalArgumentException.class,
                    () -> Decisions.isYes(null, null, new Criteria("Yes", "No"), threshold));
        }
        for (double threshold : new double[] {0.0, -0.0, 0.5, 1.0}) {
            assertThrows(DecisionGatorException.class,
                    () -> Decisions.isYes(null, null, threshold));
        }
    }

    @Test
    void missingAssetsCanBeRetriedWithoutPoisoningClassInitialization() {
        ClassLoader loader = Decisions.class.getClassLoader();
        for (String platform : new String[] {"macos-arm64", "linux-x64", "windows-x64"}) {
            assumeTrue(loader.getResource("META-INF/decisiongator/" + platform + "/bundle.index") == null,
                    "This test exercises the API without a platform bundle on the classpath");
        }
        for (int attempt = 0; attempt < 2; attempt++) {
            IllegalStateException failure = assertThrows(IllegalStateException.class,
                    () -> Decisions.isYesP("Cancel my subscription.", "Is cancellation requested?"));
            assertTrue(failure.getMessage().contains("No DecisionGator bundle"));
            assertThrows(IllegalStateException.class,
                    () -> Decisions.isYes("Cancel my subscription.", "Is cancellation requested?"));
            assertThrows(IllegalStateException.class, () -> Decisions.chooseP(CONTENT, QUESTION, TEAMS));
            assertThrows(IllegalStateException.class, () -> Decisions.choose(CONTENT, QUESTION, TEAMS));
        }
    }
}
