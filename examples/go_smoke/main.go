// Call DecisionGate from Go through its C interface (cgo).
// The library loads its model from the bundle beside it on the first call.
// By default this links the bundle for this platform under released/; to use
// another bundle, set CGO_LDFLAGS="-L/path/to/bundle -Wl,-rpath,/path/to/bundle".
package main

/*
#cgo CFLAGS: -I${SRCDIR}/../../code/include
#cgo LDFLAGS: -ldecisiongate
#cgo darwin LDFLAGS: -L${SRCDIR}/../../released/macos-arm64 -Wl,-rpath,${SRCDIR}/../../released/macos-arm64
#cgo linux LDFLAGS: -L${SRCDIR}/../../released/linux-x64 -Wl,-rpath,${SRCDIR}/../../released/linux-x64
#cgo windows LDFLAGS: -L${SRCDIR}/../../released/windows-x64
#include <stdlib.h>
#include "decisiongate.h"
*/
import "C"

import (
	"errors"
	"fmt"
	"os"
	"unsafe"
)

// Criteria spell out what counts as yes and what counts as no.
type Criteria struct{ Yes, No string }

// Ranked is one option's index into the caller's options and its probability.
type Ranked struct {
	Index int
	P     float64
}

// cstr borrows a Go string's bytes for the length of one call. The library
// takes explicit byte lengths, so no terminating NUL is needed.
func cstr(s string) (*C.char, C.size_t) {
	return (*C.char)(unsafe.Pointer(unsafe.StringData(s))), C.size_t(len(s))
}

func lastError(status C.dg_status) error {
	var required C.size_t
	C.dg_last_error(nil, 0, &required)
	if required == 0 {
		return fmt.Errorf("DecisionGate error %d", int(status))
	}
	buffer := make([]byte, int(required))
	C.dg_last_error((*C.char)(unsafe.Pointer(&buffer[0])), required, &required)
	return fmt.Errorf("DecisionGate error %d: %s", int(status), buffer[:len(buffer)-1])
}

// withCriteria passes nil for no criteria, or a C struct borrowing the strings.
func withCriteria(c *Criteria, call func(*C.dg_criteria) C.dg_status) C.dg_status {
	if c == nil {
		return call(nil)
	}
	var cc C.dg_criteria
	cc.yes, cc.yes_bytes = cstr(c.Yes)
	cc.no, cc.no_bytes = cstr(c.No)
	return call(&cc)
}

// IsYes answers a yes/no question about content. A nil error with false is a
// real "no"; failures are always returned as errors, never disguised as "no".
func IsYes(content, question string, criteria *Criteria, threshold float64) (bool, error) {
	text, textBytes := cstr(content)
	q, qBytes := cstr(question)
	var yes C.uint8_t
	status := withCriteria(criteria, func(c *C.dg_criteria) C.dg_status {
		return C.dg_is_yes_at_threshold(text, textBytes, q, qBytes, c, C.double(threshold), &yes)
	})
	if status != C.DG_OK {
		return false, lastError(status)
	}
	return yes == 1, nil
}

// IsYesP returns the probability of yes, from 0 to 1.
func IsYesP(content, question string, criteria *Criteria) (float64, error) {
	text, textBytes := cstr(content)
	q, qBytes := cstr(question)
	var p C.double
	status := withCriteria(criteria, func(c *C.dg_criteria) C.dg_status {
		return C.dg_is_yes_p(text, textBytes, q, qBytes, c, &p)
	})
	if status != C.DG_OK {
		return 0, lastError(status)
	}
	return float64(p), nil
}

// ChooseP ranks the options, best first, with probabilities that sum to one.
func ChooseP(content, question string, options []string, criteria *Criteria) ([]Ranked, error) {
	if len(options) == 0 {
		return nil, errors.New("no options")
	}
	// The option pointer array must live in C memory, so copy the options there.
	n := len(options)
	ptrs := (*[1 << 20]*C.char)(C.malloc(C.size_t(n) * C.size_t(unsafe.Sizeof((*C.char)(nil)))))[:n:n]
	sizes := make([]C.size_t, n)
	for i, option := range options {
		ptrs[i] = C.CString(option)
		sizes[i] = C.size_t(len(option))
	}
	defer func() {
		for _, p := range ptrs {
			C.free(unsafe.Pointer(p))
		}
		C.free(unsafe.Pointer(&ptrs[0]))
	}()
	text, textBytes := cstr(content)
	q, qBytes := cstr(question)
	index := make([]C.int32_t, n)
	prob := make([]C.double, n)
	status := withCriteria(criteria, func(c *C.dg_criteria) C.dg_status {
		return C.dg_choose_p(text, textBytes, q, qBytes, &ptrs[0], &sizes[0], C.size_t(n), c, &index[0], &prob[0])
	})
	if status != C.DG_OK {
		return nil, lastError(status)
	}
	ranked := make([]Ranked, n)
	for i := range ranked {
		ranked[i] = Ranked{int(index[i]), float64(prob[i])}
	}
	return ranked, nil
}

func main() {
	ticket := "Our whole warehouse can't print shipping labels and trucks leave in an hour."
	question := "Is the customer describing an urgent problem?"

	// A yes/no decision at the usual 0.5 cutoff.
	urgent, err := IsYes(ticket, question, nil, 0.5)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Could not evaluate the question:", err)
		os.Exit(1)
	}
	fmt.Println("urgent:", urgent)

	// The probability, so you can keep an uncertain range for a person.
	p, err := IsYesP(ticket, question, nil)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf("p_yes = %.3f\n", p)

	// Criteria and a stricter threshold.
	confident, err := IsYes(ticket, question, &Criteria{
		Yes: "Work is blocked and there is a deadline within hours.",
		No:  "The problem is an inconvenience with no near deadline.",
	}, 0.90)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("confident urgent:", confident)

	// Several options instead of yes or no.
	teams := []string{"billing", "technical support", "sales"}
	ranked, err := ChooseP("My card was charged twice for last month's invoice.",
		"Which team should handle this message?", teams, nil)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	for _, r := range ranked {
		fmt.Printf("%-18s %.3f\n", teams[r.Index], r.P)
	}
}
