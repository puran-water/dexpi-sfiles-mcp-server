import { Component } from "./Component";
import { getDebug, getDebugColor } from "./debug";
import { getShapeFromExtent } from "./drawExtent";
import { getPaper, PaperGroup } from "./paper";
import { ProteusXmlDrawing } from "./ProteusXmlDrawing";
import { Ellipse } from "./types/Ellipse";

/**
 * used to draw line, polyline and centerline
 * @param ctx
 * @param unit
 * @param pageOriginX
 * @param pageOriginY
 * @param offsetX
 * @param offsetY
 */
export function drawEllipse(
    ctx: Ellipse,
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
    const Size = getPaper().Size;
    const Rectangle = getPaper().Rectangle;

    const x = ctx.Position[0].Location[0].x.valueAsNumber + offsetX;
    const y = ctx.Position[0].Location[0].y.valueAsNumber + offsetY;

    const point = new Point(x * unit, pageOriginY * unit - y * unit);

    const rectangle = new Rectangle(
        point,
        new Size(ctx.primaryAxis.valueAsNumber * unit, ctx.secondaryAxis.valueAsNumber * unit)
    );
    const ellipse = new Path.Ellipse(rectangle);

    const cos = ctx.Position[0]?.Reference[0]?.x?.valueAsNumber;
    if (cos && cos !== 1) {
        ellipse.rotate(-(cos / (Math.PI / 180)) * Math.PI, point);
    }

    const sin = ctx.Position[0]?.Reference[0]?.y?.valueAsNumber;
    if (sin && sin !== 0) {
        ellipse.rotate(-(sin / (Math.PI / 90)) * Math.PI, point);
    }

    const flipY = ctx.Position[0].Axis[0].z.valueAsNumber === -1;
    if (flipY) {
        console.log("not implented flipY", ctx, cos, sin, flipY);
    }

    if (group) {
        group.addChild(ellipse);
    } else {
        ellipse.onClick = function () {
            proteusXmlDrawing.publicEvent("onClick", ctx);
        };
    }

    ellipse.strokeColor = new Color({
        red: ctx.Presentation[0].r.value,
        green: ctx.Presentation[0].g.value,
        blue: ctx.Presentation[0].b.value
    });

    ellipse.strokeWidth = ctx.Presentation[0].lineWeight.valueAsNumber * unit;

    if (ctx.filled?.value) {
        ellipse.fillColor = new Color("black");
    }

    getShapeFromExtent(
        ctx as any,
        unit,
        pageOriginX,
        pageOriginY,
        offsetX,
        offsetY,
        getDebug().circle,
        getDebugColor().circleArc,
        proteusXmlDrawing
    );
}
