/**
 * this is just for development help only
 */

type Color = { red: number; green: number; blue: number; alpha: number };

const debug = {
    text: false,
    trimmedCurve: false,
    circle: false,
    circleArc: false,
    ellipse: false,
    ellipseArc: false,
    shape: false,
    component: false,
    line: false,
    printIdMap: false,
    highlightIds: false
};

export function getDebug() {
    return debug;
}

export function setDebug(property: string, color: Color) {
    debugColor[property] = color;
}

const debugColor: Record<string, Color> = {
    text: { red: 0, green: 0, blue: 1, alpha: 0.5 },
    trimmedCurve: { red: 0, green: 1, blue: 0, alpha: 0.5 },
    circle: { red: 1, green: 1, blue: 0, alpha: 0.5 },
    circleArc: { red: 1, green: 1, blue: 0, alpha: 0.5 },
    ellipse: { red: 1, green: 1, blue: 0, alpha: 0.5 },
    ellipseArc: { red: 1, green: 1, blue: 0, alpha: 0.5 },
    component: { red: 0.5, green: 1, blue: 1, alpha: 0.5 },
    shape: { red: 1, green: 0.5, blue: 1, alpha: 0.5 },
    line: { red: 1, green: 0, blue: 0, alpha: 0.5 }
};

export function getDebugColor() {
    return debugColor;
}

export function setDebugColor(property: string, color: Color) {
    debugColor[property] = color;
}
