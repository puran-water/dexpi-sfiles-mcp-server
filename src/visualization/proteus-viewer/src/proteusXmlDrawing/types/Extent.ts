import type { Max } from "./Max";
import type { Min } from "./Min";

/**
 * A minimum bounding geometry describing the minimum and maximum coordinates of the descendants of this elements parent.
 */
export type Extent = {
    Max: Max[];
    Min: Min[];
};
