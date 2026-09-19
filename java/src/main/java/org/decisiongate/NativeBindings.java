package org.decisiongate;

import com.sun.jna.IntegerType;
import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Pointer;
import com.sun.jna.Structure;
import com.sun.jna.ptr.DoubleByReference;
import com.sun.jna.ptr.PointerByReference;

interface NativeBindings extends Library {
    class SizeT extends IntegerType {
        private static final long serialVersionUID = 1L;
        public SizeT() { this(0); }
        public SizeT(long value) { super(Native.SIZE_T_SIZE, value, true); }
    }

    @Structure.FieldOrder({"yes", "yesBytes", "no", "noBytes"})
    class NativeCriteria extends Structure {
        public Pointer yes;
        public SizeT yesBytes;
        public Pointer no;
        public SizeT noBytes;

        public NativeCriteria() {
            yesBytes = new SizeT();
            noBytes = new SizeT();
        }
    }

    int dg_load(Pointer path, SizeT pathBytes, PointerByReference model);
    int dg_evaluate(Pointer model, Pointer content, SizeT contentBytes,
                    Pointer question, SizeT questionBytes, NativeCriteria criteria,
                    DoubleByReference probability);
    // options/optionBytes are a Memory block of pointers and a Memory block of size_t
    // lengths, one entry per option, matching how single strings are passed via Utf8.
    int dg_evaluate_choice(Pointer model, Pointer content, SizeT contentBytes,
                    Pointer question, SizeT questionBytes,
                    Pointer options, Pointer optionBytes, SizeT optionCount,
                    NativeCriteria criteria, int[] outIndex, double[] outP);
    int dg_metadata(Pointer model, Pointer buffer, SizeT capacity, Pointer required);
    int dg_last_error(Pointer buffer, SizeT capacity, Pointer required);
    void dg_release(Pointer model);
}
