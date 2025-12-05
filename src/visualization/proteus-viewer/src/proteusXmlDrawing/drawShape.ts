import { Component } from "./Component";
import { getDebug, getDebugColor } from "./debug";
import { getShapeFromExtent } from "./drawExtent";
import { getPaper, PaperGroup } from "./paper";
import { ProteusXmlDrawing } from "./ProteusXmlDrawing";
import { Shape } from "./types/Shape";

/**
 * used to draw line, polyline and centerline
 * @param ctx
 * @param unit
 * @param pageOriginX
 * @param pageOriginY
 * @param offsetX
 * @param offsetY
 */
export function drawShape(
    ctx: Shape,
    unit: number,
    pageOriginX: number,
    pageOriginY: number,
    offsetX = 0,
    offsetY = 0,
    group: PaperGroup | undefined,
    caller: Component,
    proteusXmlDrawing: ProteusXmlDrawing
) {
    const Point = getPaper().Point;
    const Path = getPaper().Path;
    const Color = getPaper().Color;

    const segments: any[] = [];

    ctx.Coordinate.forEach((coordinate) => {
        const x = coordinate.x.valueAsNumber + offsetX;
        const y = coordinate.y.valueAsNumber + offsetY;
        const point = new Point(x * unit, pageOriginY * unit - y * unit);
        segments.push(point);
    });

    const path = new Path(segments);
    if (group) {
        group.addChild(path);
    } else {
        path.onClick = function () {
            proteusXmlDrawing.publicEvent("onClick", ctx);
        };
    }

    path.strokeColor = new Color({
        red: ctx.Presentation[0].r.value,
        green: ctx.Presentation[0].g.value,
        blue: ctx.Presentation[0].b.value
    });

    path.strokeWidth = ctx.Presentation[0].lineWeight.valueAsNumber * unit;

    if (ctx.filled) {
        path.fillColor = new Color({
            red: ctx.Presentation[0].r.value,
            green: ctx.Presentation[0].g.value,
            blue: ctx.Presentation[0].b.value
        });
    }

    getShapeFromExtent(
        ctx as any,
        unit,
        pageOriginX,
        pageOriginY,
        offsetX,
        offsetY,
        getDebug().shape,
        getDebugColor().shape,
        proteusXmlDrawing
    );
}
