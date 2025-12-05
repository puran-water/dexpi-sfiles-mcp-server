import { Component } from "./Component";

export class Attribute {
    public value: string | null;
    valueAsString: string;
    valueAsNumber: number;
    constructor(public element: Element, public attributeName: string, public parent: Component) {
        this.value = element.getAttribute(attributeName);
        this.valueAsString = this.value || "";
        this.valueAsNumber = parseFloat(this.value || "");

        // make it simpler to see attributes
        parent.attributes[attributeName] = this.valueAsString;

        if (isNaN(this.valueAsNumber)) {
            this.valueAsNumber = 0;
        }
    }
}
