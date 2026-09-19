package org.decisiongate;

/**
 * One ranked option from a multiple-choice decision.
 *
 * @param index index of this option in the caller's options list
 * @param p calibrated probability of this option, between zero and one, inclusive
 */
public record Choice(int index, double p) {
}
