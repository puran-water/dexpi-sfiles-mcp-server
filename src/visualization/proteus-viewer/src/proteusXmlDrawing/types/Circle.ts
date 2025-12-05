import { Attribute } from "../Attribute";
import { Extent } from "./Extent";
import { Position } from "./Position";
import { Presentation } from "./Presentation";

export type Circle = {
    /**
     * The style to use when drawing the circle
     */
    Presentation: Presentation[];
    /**
     * The minimum bounding geometry of the circle
     */
    Extent: Extent[];
    /**
     * The location of the circles centre
     */
    Position: Position[];
    /**
     * One of ‘Solid’ or ‘Hatch’.  If not present the circle is not filled.
     */
    filled: Attribute;
    /**
     * The radius of the circle to draw
     */
    radius: Attribute;
};
