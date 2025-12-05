import { Component } from "./Component";

export function getChildComponents(ctx: Record<string, any>) {
    const drawable: Component[] = [];
    const objectProperties = Object.keys(ctx);

    objectProperties.forEach((prop) => {
        if (Array.isArray(ctx[prop])) {
            ctx[prop].forEach((child: any) => {
                if (child && typeof child.draw === "function") {
                    drawable.push(child);
                }
            });
        }
    });
    return drawable;
}
