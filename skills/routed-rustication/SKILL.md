# routed-rustication

Subtractive routed lower-floor rustication around openings.

## Core strategy

1. Start from intact shallow cladding.
2. Construct conceptual course polyline around opening.
3. Split into straight segments.
4. Build overlapping trapezoidal-prism cutters per segment.
5. Boolean-difference cutters from cladding.
6. Cut opening after routing.
7. Add keystone/ornament separately.
