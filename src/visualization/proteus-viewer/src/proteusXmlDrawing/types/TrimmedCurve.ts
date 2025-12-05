import { Attribute } from "../Attribute";
import { Extent } from "./Extent";
import { Position } from "./Position";
import { Presentation } from "./Presentation";

export type TrimmedCurve = {
    /**
     * Only present if Ellipse isn’t present.  The base Circle used to define the arc
     */
    Circle: Presentation[];
    /**
     * Only present if Circle isn’t present.  The base ellipse used to define the arc.
     */
    Ellipse: Extent[];
    /**
     * Any application specific attributes
     */
    GenericAttributes: Position[];
    /**
     * The rotation around the circle/ellipse to start the arc from.  0 = east.  The angle is specified in degrees (0-360) measured anti-clockwise
     */
    startAngle: Attribute;
    /**
     * The rotation around the circle/ellipse to end the arc at.  0 = east.
     * The angle is specified in degrees (0-360) measured anti-clockwise.
     */
    endAngle: Attribute;
};
