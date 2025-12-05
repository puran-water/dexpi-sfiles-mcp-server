import { Attribute } from "./Attribute";
import { getChildComponents } from "./getChildComponents";
import { addToShapeCatalogStore, getFromShapeCatalogStore } from "./shapeCatalogStore";
import { drawLine } from "./drawLine";
import { drawShape } from "./drawShape";
import { drawCircle } from "./drawCircle";
import { drawtext } from "./drawText";
import { drawTrimmedCurve } from "./drawTrimmedCurve";
import { drawEllipse } from "./drawEllipse";
import { addToIdStore } from "./idStore";
import { getPaper, PaperGroup } from "./paper";
import { Color, Point } from "paper/dist/paper-core";
import { getDebug, getDebugColor } from "./debug";
import { getShapeFromExtent } from "./drawExtent";
import { ProteusXmlDrawing } from "./ProteusXmlDrawing";
import { ExternalSymbol } from "../symbolLibrary";

/** Union type for items from shape catalog store (embedded or external symbols) */
export type ShapeCatalogItem = Component | ExternalSymbol;

export class Component {
    isChild = true;
    tagName!: Attribute;
    elementTagName: string;
    attributes: Record<string, string> = {};
    GenericAttributes: Component[] = [];
    shapeCatalogItem?: ShapeCatalogItem;
    /*
     * will be in component type of GenericAttributes only...
     */
    GenericAttribute: Component[] = [];
    genericAttributes: Record<string, any> = {};
    componentName?: Attribute;
    iD?: Attribute;
    Position: any[] = [];
    Extent: any[] = [];
    Presentation: any[] = [];
    Scale: any[] = [];

    /**
     * Component
     * @param element
     * @param isShapeCatalogChild
     * @param parent
     */
    constructor(
        public element: Element,
        public isShapeCatalogChild: boolean,
        public parent?: Component
    ) {
        this.elementTagName = this.element.tagName;
        if (this.elementTagName === "ShapeCatalogue") {
            this.isShapeCatalogChild = true;
        }

        for (let i = 0; i < this.element.children.length; i++) {
            const childElement = this.element.children[i];
            const childTag = childElement.tagName;
            const root = this as any;

            if (!root[childTag]) {
                root[childTag] = [];
            }
            const componentClass = new Component(childElement, this.isShapeCatalogChild, this);
            root[childTag].push(componentClass);
        }

        const attributes = element.getAttributeNames();
        attributes.forEach((attributeName) => {
            const root = this as any;
            // need to keep them as lowercase to be sure we dont crash with component classes
            const attributeNameLowercase =
                attributeName[0].toLowerCase() + attributeName.substring(1, attributeName.length);
            root[attributeNameLowercase] = new Attribute(element, attributeName, this);
        });

        /**
         * add simplified property 'genericAttributes' so its easy to read all generic attributes
         */

        if (this.GenericAttribute.length) {
            this.GenericAttribute.forEach((e) => {
                this.genericAttributes[e.attributes.Name] = e.attributes.Value;
            });
        }

        if (this.GenericAttributes.length) {
            this.GenericAttributes.forEach((e, i) => {
                this.genericAttributes[`${i + 1}: ${e.attributes.Set || ""}`] = e.genericAttributes;
            });
        }

        if (this.elementTagName !== "ShapeCatalogue") {
            // need to build a map, so other components can get details
            if (this.isShapeCatalogChild) {
                if (this.componentName?.value) {
                    addToShapeCatalogStore(this.componentName?.value, this);
                }
            }
        }

        if (this.iD?.valueAsString) {
            // need to build a map, so other components can get details

            addToIdStore(this.iD.valueAsString, this);
        }
    }

    /**
     * Handles all draw loggic
     * @param unit
     * @param pageOriginX
     * @param pageOriginY
     * @param offsetX - used when its a shape component
     * @param offsetY - used when its a shape component
     * @returns
     */
    draw(
        unit: number,
        pageOriginX: number,
        pageOriginY: number,
        offsetX = 0,
        offsetY = 0,
        group: PaperGroup | undefined,
        caller: Component,
        proteusXmlDrawing: ProteusXmlDrawing
    ) {
        if (this.elementTagName === "ShapeCatalogue") {
            // shape catalog should never draw, it will be called by others using componentName
            return;
        }

        if (this.elementTagName === "TrimmedCurve") {
            drawTrimmedCurve(
                this as any,
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                group,
                caller,
                proteusXmlDrawing
            );

            // important - we handle all children in draw function above, so lets return
            return;
        }
        /**
         * draw children
         */
        const drawables = getChildComponents(this);
        drawables.forEach((drawable) => {
            drawable.draw(
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                group,
                this,
                proteusXmlDrawing
            );
        });
        /**
         * check if anything i shape catalog
         */
        if (this.componentName?.value && this.Position?.length) {
            const shapeCatalogItem = getFromShapeCatalogStore<ShapeCatalogItem>(this.componentName.value);
            if (shapeCatalogItem && shapeCatalogItem !== (this as unknown)) {
                // need to get locatioin, so we can send it as offset

                const Pgroup = getPaper().Group;
                const group = new Pgroup();

                this.shapeCatalogItem = shapeCatalogItem;

                const that = this as any;
                group.onClick = function () {
                    proteusXmlDrawing.publicEvent("onClick", that);
                };

                const x = this.Position[0].Location[0].x.valueAsNumber + offsetX;
                const y = this.Position[0].Location[0].y.valueAsNumber + offsetY;
                const point = new Point(x * unit, pageOriginY * unit - y * unit);

                if (typeof (shapeCatalogItem as any).draw === "function") {
                    (shapeCatalogItem as any).draw(
                        unit,
                        pageOriginX,
                        pageOriginY,
                        x + offsetX,
                        y + offsetY,
                        group,
                        this,
                        proteusXmlDrawing
                    );
                }

                if (this.Scale.length) {
                    const scaleX = parseFloat(this.Scale[0].attributes.X);
                    const scaleY = parseFloat(this.Scale[0].attributes.Y);
                    if (scaleX !== 1 || scaleY !== 1) {
                        group.scale(scaleX, scaleY, point);
                    }
                }

                const cos = this.Position[0]?.Reference[0]?.x?.valueAsNumber;
                if (cos && cos !== 1) {
                    group.rotate(-(cos / (Math.PI / 180)) * Math.PI, point);
                }

                const sin = this.Position[0]?.Reference[0]?.y?.valueAsNumber;
                if (sin && sin !== 0) {
                    group.rotate(-(sin / (Math.PI / 90)) * Math.PI, point);
                }

                const flipY = this.Position[0]?.Axis[0]?.z?.valueAsNumber === -1;
                if (flipY) {
                    group.scale(1, -1, point);
                }

                getShapeFromExtent(
                    this as any,
                    unit,
                    pageOriginX,
                    pageOriginY,
                    offsetX,
                    offsetY,
                    getDebug().component,
                    getDebugColor().component,
                    proteusXmlDrawing
                );
            } else {
                if (group) {
                    // of not shape catalog we still need to rotate shape if any rotation
                    /*   console.log("shapeCatalogItem") */
                    const x = this.Position[0].Location[0].x.valueAsNumber + offsetX;
                    const y = this.Position[0].Location[0].y.valueAsNumber + offsetY;
                    const point = new Point(x * unit, pageOriginY * unit - y * unit);

                    if (this.Scale.length) {
                        const scaleX = parseFloat(this.Scale[0].attributes.X);
                        const scaleY = parseFloat(this.Scale[0].attributes.Y);
                        if (scaleX !== 1 || scaleY !== 1) {
                            group.scale(scaleX, scaleY, point);
                        }
                    }

                    const cos = this.Position[0]?.Reference[0]?.x?.valueAsNumber;
                    if (cos && cos !== 1) {
                        group.rotate(-(cos / (Math.PI / 180)) * Math.PI, point);
                    }

                    const sin = this.Position[0]?.Reference[0]?.y?.valueAsNumber;
                    if (sin && sin !== 0) {
                        group.rotate(-(sin / (Math.PI / 90)) * Math.PI, point);
                    }

                    const flipY = this.Position[0]?.Axis[0]?.z?.valueAsNumber === -1;

                    if (flipY) {
                        group.scale(1, -1, point);
                    }
                }
            }
        }

        /**
         * Lines
         */
        if (
            this.elementTagName === "Line" ||
            this.elementTagName === "PolyLine" ||
            this.elementTagName === "CenterLine"
        ) {
            drawLine(
                this as any,
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                group,
                caller,
                proteusXmlDrawing
            );
        }

        /**
         * BsplineCurve
         */
        if (this.elementTagName === "BsplineCurve") {
            console.warn("BsplineCurve not implemented", this);
        }

        /**
         * CompositeCurve
         */
        if (this.elementTagName === "CompositeCurve") {
            console.warn("CompositeCurve not implemented", this);
        }

        /**
         * Circle
         */
        if (this.elementTagName === "Circle") {
            drawCircle(
                this as any,
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                group,
                caller,
                proteusXmlDrawing
            );
        }

        /**
         * Ellipse
         */
        if (this.elementTagName === "Ellipse") {
            drawEllipse(
                this as any,
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                group,
                caller,
                proteusXmlDrawing
            );
        }

        /**
         * Shape
         */
        if (this.elementTagName === "Shape") {
            drawShape(
                this as any,
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                group,
                caller,
                proteusXmlDrawing
            );
        }

        /**
         * Text
         */
        if (this.elementTagName === "Text") {
            drawtext(
                this as any,
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                group,
                caller,
                proteusXmlDrawing
            );
        }

        if (getDebug().highlightIds) {
            getShapeFromExtent(
                this as any,
                unit,
                pageOriginX,
                pageOriginY,
                offsetX,
                offsetY,
                getDebug().component,
                getDebugColor().component,
                proteusXmlDrawing
            );
        }
    }
}
