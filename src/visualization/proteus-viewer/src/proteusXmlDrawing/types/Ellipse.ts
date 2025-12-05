import { Attribute } from "../Attribute";
import { Extent } from "./Extent";
import { Position } from "./Position";
import { Presentation } from "./Presentation";

export type Ellipse = {
    /**
     * The style to use when drawing the ellipse
     */
    Presentation: Presentation[];
    /**
     * The minimum bounding geometry of the geometric contents of the Drawing element and its descendants
     */
    Extent: Extent[];
    /**
     * The centre/origin of the ellipse to draw
     */
    Position: Position[];
    /**
     * Any application specific attributes
     */
    GenericAttributes: Position[];
    /**
     * One of ‘Solid’ or ‘Hatch’.  If not present the circle is not filled.
     */
    filled: Attribute;
    /**
     * Double describing the primary axis
     */
    primaryAxis: Attribute;
    /**
     * Double describing the secondary  axis
     */
    secondaryAxis: Attribute;
};
