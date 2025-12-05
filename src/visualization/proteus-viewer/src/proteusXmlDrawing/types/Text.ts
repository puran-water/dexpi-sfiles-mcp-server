import { Attribute } from "../Attribute";
import { Component } from "../Component";
import { Extent } from "./Extent";
import { Position } from "./Position";
import { Presentation } from "./Presentation";

export type Text = {
    /**
     * The style to use to draw the text.
     */
    Presentation: Presentation[];
    /**
     * The minimum bounding rectangle around the text.
     */
    Extent: Extent[];
    /**
     * The position of the text
     */
    Position: Position[];
    /**
     * Any application specific attributes, this could include attributes that contain the text content to write.
     */
    GenericAttributes: Component[]; // todo: improve just not very important in the begining, bigger issues with text
    /**
     * All attributes easly accessable
     */
    attributes: Record<string, string>;
    /**
     * The number of text lines being represented.  If not present then a value of 1 is assumed.
     */
    numLines: Attribute;
    /**
     * If present this is the text to be drawn.
     * If the text contains a line break then it should be split into the String child elements instead of being
     * in the attribute or the line break character replaced with an appropriate character reference.
     */
    string: Attribute;
    /**
     * The font family name to use
     */
    font: Attribute;
    /**
     * The location of Position within the Text to be written.  Where the text is on multiple lines then Justification denotes the location of Position for the first line of text.
     *
     * One of the following :
     * LeftTop
     * LeftCenter
     * LeftBottom
     * CenterTop
     * CenterCenter
     * CenterBottom
     * RightTop
     * RightCenter
     * RightBottom
     *
     * Defaults to LeftBottom if not provided.
     *
     */
    justification: Attribute;
    /**
     * The full width of the Text string once rendered
     */
    width: Attribute;
    /**
     * The full height of the Text string once rendered
     */
    height: Attribute;
    /**
     * This is the angle that the base line of the text string makes with the positive X axis measured anticlockwise in degrees [1].
     */
    textAngle: Attribute;
    /**
     * This is the angle, in degrees, of slant of the text characters measured clockwise from the positive Y axis.
     * Eg. for the character I it is the angle that the vertical stroke makes with the positive Y axis [1].
     */
    slantAngle: Attribute;
    /**
     * If provided then the text string is to be constructed from the attributes of another element.
     * The ID may be provided as the ID of the element, the PersistentID/@Identifier or the TagName of the element.
     * See TagName Referencing
     */
    itemID: Attribute;
    /**
     * If the text is to be obtained from a child of a GenericAttributes element then the set name for
     * the GenericAttributes element may be provided to avoid ambiguity
     */
    set: Attribute;
    /**
     * The template for the textual contents if obtaining the text from referenced attributes.
     *
     * The value of the DependantAttribute can contain a single attribute or a list of Attributes and explicit text.
     * IF a single attribute is referenced it may appear just as the attribute name. Where multiple attributes or explicit text is used
     * the attribute names are contained in square brackets. Eg “[Tagprefix]-[Tagnumber][Tagsuffix]”.
     *
     * The search order will be the Attributes of the PlantItem, ItemAttributes then GenericAttributes of the Text
     * followed by the GenericAttributes of the parent or the object explicitly identified by the ItemID. The first occurrence
     * of the named Attribute will be used, there is no mechanism for handling multiple attributes of the same name.
     *
     */
    dependantAttribute: Attribute;
};
