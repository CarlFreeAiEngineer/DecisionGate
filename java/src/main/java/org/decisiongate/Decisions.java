package org.decisiongate;

import java.nio.file.Path;
import java.util.List;

/**
 * Evaluate decisions using the component packaged with the application.
 * The first valid call loads one shared session; later calls reuse it safely
 * across threads. Initialization failures can be retried on a later call.
 * A JVM shutdown hook closes the shared session before native runtime teardown;
 * the native libraries remain loaded until process exit.
 * No caller cleanup is needed. Hot class-loader replacement is unsupported;
 * finish inference before process exit and do not call from exit hooks.
 * Set the optional {@code decisiongate.cache} system property before first use
 * to choose the extraction directory instead of {@code ~/.cache/decisiongate}.
 */
public final class Decisions {
    private static DecisionGate model;
    private static boolean shuttingDown;

    private Decisions() { }

    /**
     * Answer yes when the calibrated probability is at least 0.5.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @return whether the probability is at least 0.5
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static boolean isYes(String content, String question) {
        return isYes(content, question, null, 0.5);
    }

    /**
     * Answer yes when the calibrated probability reaches the supplied threshold.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @param threshold finite probability between zero and one, inclusive
     * @return whether the probability is greater than or equal to the threshold
     * @throws IllegalArgumentException if the threshold is invalid
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static boolean isYes(String content, String question, double threshold) {
        return isYes(content, question, null, threshold);
    }

    /**
     * Answer yes using explicit criteria and a threshold of 0.5.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @param criteria explicit answer descriptions, or null for defaults
     * @return whether the probability is at least 0.5
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static boolean isYes(String content, String question, Criteria criteria) {
        return isYes(content, question, criteria, 0.5);
    }

    /**
     * Answer yes using explicit criteria and the supplied threshold.
     * A failed evaluation throws; it never becomes a no answer.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @param criteria explicit answer descriptions, or null for defaults
     * @param threshold finite probability between zero and one, inclusive
     * @return whether the probability is greater than or equal to the threshold
     * @throws IllegalArgumentException if the threshold is invalid
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static boolean isYes(String content, String question, Criteria criteria, double threshold) {
        if (!Double.isFinite(threshold) || threshold < 0 || threshold > 1) {
            throw new IllegalArgumentException("threshold must be finite and between 0 and 1, inclusive");
        }
        return isYesP(content, question, criteria) >= threshold;
    }

    /**
     * Return the calibrated probability of a yes answer.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @return calibrated probability between zero and one, inclusive
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static double isYesP(String content, String question) {
        return isYesP(content, question, null);
    }

    /**
     * Return a probability using optional explicit yes/no descriptions.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank yes/no question about the content
     * @param criteria explicit answer descriptions, or null for defaults
     * @return calibrated probability between zero and one, inclusive
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static double isYesP(String content, String question, Criteria criteria) {
        Utf8.validate(content, "content");
        Utf8.validate(question, "question");
        return sharedModel().evaluate(content, question, criteria);
    }

    /**
     * Rank options best first for a question about the content.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @return every option ranked best first, as index/probability pairs summing to one
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static List<Choice> chooseP(String content, String question, List<String> options) {
        return chooseP(content, question, options, null);
    }

    /**
     * Rank options best first using optional explicit yes/no descriptions.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @param criteria explicit answer descriptions applied to every option, or null for defaults
     * @return every option ranked best first, as index/probability pairs summing to one
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static List<Choice> chooseP(String content, String question, List<String> options, Criteria criteria) {
        Utf8.validate(content, "content");
        Utf8.validate(question, "question");
        Utf8.validateOptions(options);
        return sharedModel().evaluateChoice(content, question, options, criteria);
    }

    /**
     * Return the best option's index, never below threshold zero.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @return the best option's index into the caller's options list
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static int choose(String content, String question, List<String> options) {
        return choose(content, question, options, null, 0.0);
    }

    /**
     * Return the best option's index, or -1 when its probability is below the threshold.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @param threshold finite probability between zero and one, inclusive
     * @return the best option's index, or -1 when its probability is below the threshold
     * @throws IllegalArgumentException if the threshold is invalid
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static int choose(String content, String question, List<String> options, double threshold) {
        return choose(content, question, options, null, threshold);
    }

    /**
     * Return the best option's index using explicit criteria, never below threshold zero.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @param criteria explicit answer descriptions applied to every option, or null for defaults
     * @return the best option's index into the caller's options list
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static int choose(String content, String question, List<String> options, Criteria criteria) {
        return choose(content, question, options, criteria, 0.0);
    }

    /**
     * Return the best option's index using explicit criteria and the supplied threshold.
     * A failed evaluation throws; it never becomes a partial or fabricated result.
     *
     * @param content nonblank content to evaluate
     * @param question nonblank question comparing the options
     * @param options at least two nonblank options, in the caller's order
     * @param criteria explicit answer descriptions applied to every option, or null for defaults
     * @param threshold finite probability between zero and one, inclusive
     * @return the best option's index, or -1 when its probability is below the threshold
     * @throws IllegalArgumentException if the threshold is invalid
     * @throws DecisionGateException if input is invalid or native inference fails
     * @throws IllegalStateException if packaged assets cannot be prepared
     */
    public static int choose(String content, String question, List<String> options, Criteria criteria,
            double threshold) {
        if (!Double.isFinite(threshold) || threshold < 0 || threshold > 1) {
            throw new IllegalArgumentException("threshold must be finite and between 0 and 1, inclusive");
        }
        Choice best = chooseP(content, question, options, criteria).get(0);
        return best.p() >= threshold ? best.index() : -1;
    }

    private static synchronized DecisionGate sharedModel() {
        if (shuttingDown) {
            throw new IllegalStateException("DecisionGate is shutting down");
        }
        if (model == null) {
            String cache = System.getProperty("decisiongate.cache");
            DecisionGate loaded = cache == null ? DecisionGate.loadBundled()
                    : DecisionGate.loadBundled(Path.of(cache));
            try {
                // Java hooks run before the native atexit callback releases the
                // ONNX environment. Release only; never initialize or infer here.
                Runtime.getRuntime().addShutdownHook(
                        new Thread(Decisions::closeAtShutdown, "decisiongate-release"));
            } catch (RuntimeException | Error failure) {
                loaded.close();
                throw failure;
            }
            model = loaded;
        }
        return model;
    }

    private static synchronized void closeAtShutdown() {
        shuttingDown = true;
        if (model != null) {
            // close() shares the evaluation lock, so an in-flight call finishes
            // before its session is released. Later evaluations are rejected.
            model.close();
        }
    }
}
