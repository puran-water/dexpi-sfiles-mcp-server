import { Component } from "./Component";
import { clearStore } from "./idStore";
import { getPaper, initPaper } from "./paper";

type callable = { handleEvent: (e: { type: string; data: any }) => void };

export class ProteusXmlDrawing {
    private xml: Document;
    private canvas: HTMLCanvasElement;
    private PlantModel: any;
    private root: boolean;
    private subscribers: Set<callable> = new Set();

    constructor(xmlString: string, canvasId: string) {
        this.root = true;
        this.xml = new window.DOMParser().parseFromString(xmlString, "text/xml");
        this.canvas = document.getElementById(canvasId) as HTMLCanvasElement;

        clearStore();

        initPaper(canvasId);

        const plantModelElement = this.xml.getElementsByTagName("PlantModel")[0];
        if (!plantModelElement) {
            alert("missing plantmodel");
            return;
        }
        this.PlantModel = new Component(plantModelElement, false);
    }

    public getSchemaLocation() {
        const plantModelElement = this.xml.getElementsByTagName("PlantModel")[0];
        if (plantModelElement) {
            const schemaLocation = plantModelElement.getAttribute("xsi:schemaLocation");
            if (schemaLocation) {
                return schemaLocation;
            }
            const noNamespaceSchemaLocation = plantModelElement.getAttribute(
                "xsi:noNamespaceSchemaLocation"
            );
            if (noNamespaceSchemaLocation) {
                return noNamespaceSchemaLocation;
            }
        }
        return null;
    }

    public getSchemaVersion() {
        const PlantInformation = this.xml.getElementsByTagName("PlantInformation")[0];
        if (PlantInformation) {
            const schemaVersion = PlantInformation.getAttribute("SchemaVersion");
            if (schemaVersion) {
                return schemaVersion;
            }
        }
        return null;
    }

    public addEventListener(callable: callable) {
        this.subscribers.add(callable);
    }
    public removeEventListener(callable: callable) {
        this.subscribers.delete(callable);
    }

    public publicEvent(eventName: string, data: any) {
        this.subscribers.forEach((c) => {
            c.handleEvent({ type: eventName, data });
        });
    }

    public draw() {
        // clear before we draw anything
        getPaper().project.activeLayer.removeChildren();
        getPaper().view.requestUpdate();

        const unitTypesSupported = ["Metre", "mm", "Millimetre", "m"];
        const PlantInformationUnitType = this.PlantModel.PlantInformation[0].units.value;

        if (!unitTypesSupported.includes(PlantInformationUnitType)) {
            console.warn(
                "I need to add more here",
                this.PlantModel.PlantInformation[0].units.value
            );
        }

        let unit = 1.5;
        switch (true) {
            case PlantInformationUnitType === "Metre":
                unit = 1500;
                break;
            case PlantInformationUnitType === "m":
                unit = 1500;
                break;
        }

        if (!Array.isArray(this.PlantModel.Drawing) || this.PlantModel.Drawing[0].length === 0) {
            const x = this.PlantModel.Extent[0]?.Max[0]?.x.valueAsNumber;
            const y = this.PlantModel.Extent[0]?.Max[0]?.y.valueAsNumber;
            if (unit === 1.5) {
                console.warn(
                    `No drawing element, using x:${x | 1261.5}, y:${y | 891}`,
                    this.PlantModel
                );

                this.PlantModel.draw(unit, x || 1261.5, y || 891, 0, 0);
            } else {
                console.warn(
                    `No drawing element, using x:${x | 0.12615}, y:${y | 0.891}`,
                    this.PlantModel
                );
                this.PlantModel.draw(unit, x || 0.12615, y || 0.891, 0, 0);
            }
            return;
        }

        const presentation = this.PlantModel.Drawing[0]?.Presentation[0];
        if (presentation?.attributes?.Color) {
            this.canvas.style.backgroundColor = presentation?.attributes?.Color;
        } else {
            this.canvas.style.backgroundColor = "white";
        }

        const x = this.PlantModel.Drawing[0].Extent[0].Max[0].x.valueAsNumber;
        const y = this.PlantModel.Drawing[0].Extent[0].Max[0].y.valueAsNumber;

        this.PlantModel.draw(unit, x, y, 0, 0, null, this, this);

        // scale it up to match our canvas
        /* const Point = getPaper().Point;
        getPaper().project.activeLayer.scale(
            1.5,
            new Point(getPaper().view.bounds.x, getPaper().view.bounds.y)
        );
        getPaper().view.requestUpdate(); */
    }
}
