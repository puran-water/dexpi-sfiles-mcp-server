import { Component } from "../Component";
import { XYZ } from "./XYZ";

/**
 * A Coordinate element is a Tuple of ordinates denoting a location in the drawing plane.
 * For 2D drawings the Z ordinates should always be 0.
 */
export type Cooordinate = XYZ & Component;
