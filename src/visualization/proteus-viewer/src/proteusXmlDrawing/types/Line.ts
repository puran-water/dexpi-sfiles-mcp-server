import { Attribute } from "../Attribute";
import { Cooordinate } from "./Coordinate";
import { Extent } from "./Extent";
import { Presentation } from "./Presentation";

export type Line = {
    /**
     * The style to use when drawing the line.
     * The drawing behaviour is undefined if the Presentation element is missing.
     */
    Presentation: Presentation[];
    /**
     * The minimum bounding geometry of the element and its descendants
     */
    Extent: Extent[];
    /**
     * The coordinates defining the primitive.
     * The first coordinate should match the last to complete a closed form.
     */
    Coordinate: Cooordinate[];
    /**
     * The number of child Coordinate elements.
     */
    numPoints: Attribute;
};
