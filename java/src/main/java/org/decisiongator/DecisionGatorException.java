package org.decisiongator;

/** A native component failure, or invalid input to the Java wrapper. */
public final class DecisionGatorException extends RuntimeException {
    /** Serialization format version. */
    private static final long serialVersionUID = 1L;
    /**
     * The native status code.
     * @serial
     */
    private final int statusCode;

    /**
     * Create an exception with a native status code and explanation.
     *
     * @param statusCode the DG_* status code from decisiongator.h
     * @param message explanation of the failure
     */
    public DecisionGatorException(int statusCode, String message) {
        super(message);
        this.statusCode = statusCode;
    }

    /**
     * Create an exception retaining the underlying failure.
     *
     * @param statusCode the DG_* status code from decisiongator.h
     * @param message explanation of the failure
     * @param cause underlying failure
     */
    public DecisionGatorException(int statusCode, String message, Throwable cause) {
        super(message, cause);
        this.statusCode = statusCode;
    }

    /**
     * Return the native status code.
     *
     * @return the DG_* status code from decisiongator.h
     */
    public int statusCode() {
        return statusCode;
    }
}
