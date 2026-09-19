package org.decisiongate;

/**
 * Descriptions of what counts as a yes answer and a no answer.
 *
 * @param yes nonblank description of a yes answer
 * @param no nonblank description of a no answer
 */
public record Criteria(String yes, String no) {
    /**
     * Create criteria with nonblank, valid Unicode descriptions.
     *
     * @param yes description of a yes answer
     * @param no description of a no answer
     * @throws DecisionGateException if either description is null, blank, or has an unpaired surrogate
     */
    public Criteria {
        Utf8.validate(yes, "criteria.yes");
        Utf8.validate(no, "criteria.no");
    }
}
