import { Line } from "./types/Line";
import { getPaper, PaperGroup } from "./paper";
import { Component } from "./Component";
import { getShapeFromExtent } from "./drawExtent";
import { getDebug, getDebugColor } from "./debug";
import { ProteusXmlDrawing } from "./ProteusXmlDrawing";

/**
 * used to draw line, polyline and centerline
 * @param ctx
 * @param unit
 * @param pageOriginX
 * @param pageOriginY
 * @param offsetX
 * @param offsetY
 */
export function drawLine(
    ctx: Line,
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

    if (!Array.isArray(ctx.Coordinate) || ctx.Coordinate.length === 0) {
        // who knew.. it happens in some files..
        if (ctx.numPoints?.valueAsNumber !== 0) {
            console.warn("line element without coordinate");
        }
        return;
    }

    ctx.Coordinate.forEach((coordinate) => {
        const x = coordinate.x.valueAsNumber + offsetX;
        const y = coordinate.y.valueAsNumber + offsetY;
        const point = new Point(x * unit, pageOriginY * unit - y * unit);
        segments.push(point);
    });

    const path = new Path(segments);

    path.strokeColor = new Color({
        red: ctx.Presentation[0].r.value,
        green: ctx.Presentation[0].g.value,
        blue: ctx.Presentation[0].b.value
    });

    // todo... actual dash length might be off a little..

    switch (ctx.Presentation[0].lineType?.valueAsString) {
        case "0":
            break;
        case "Solid":
            break;
        case "1":
            path.dashArray = [0.3, 0.3];
        case "Dotted":
            path.dashArray = [0.3, 0.3];
            break;
        case "2":
            path.dashArray = [2, 0.5];
        case "Dashed":
            path.dashArray = [2, 0.5];
            break;
        case "3":
            path.dashArray = [4, 0.5];
        case "Long Dash":
            path.dashArray = [4, 0.5];
            break;
        case "4":
            path.dashArray = [4, 0.5, 1, 0.5];
            break;
        case "Long Dash + Short Dash, CenterLine":
            path.dashArray = [15, 1, 0.5, 1, 0.5, 1]; // tried to make it look like sample PDF I got
            break;
        case "5":
            path.dashArray = [1, 0.5];
            break;
        case "Short Dash":
            path.dashArray = [1, 0.5];
            break;
        case "6":
            path.dashArray = [4, 0.5, 1, 0.5, 1, 0.5];
            break;
        case "Long Dash + Short Dash + Short Dash":
            path.dashArray = [4, 1, 1, 1, 1, 1];
            break;
        case "7":
            path.dashArray = [2, 0.5, 1, 0.5];
            break;
        case "Dash + Short Dash":
            path.dashArray = [2, 0.5, 1, 0.5];
            break;
        default:
            if (ctx.Presentation[0].lineType?.valueAsString !== undefined) {
                console.error("unknown linetype", ctx);
            }
    }

    path.strokeWidth = ctx.Presentation[0].lineWeight.valueAsNumber * unit;
    if (group) {
        group.addChild(path);
    } else {
        path.onClick = function () {
            proteusXmlDrawing.publicEvent("onClick", ctx);
        };
    }

    getShapeFromExtent(
        ctx as any,
        unit,
        pageOriginX,
        pageOriginY,
        offsetX,
        offsetY,
        getDebug().line,
        getDebugColor().line,
        proteusXmlDrawing
    );
}
