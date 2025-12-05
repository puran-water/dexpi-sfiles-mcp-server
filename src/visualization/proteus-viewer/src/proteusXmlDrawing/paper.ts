import paper from "paper";

export function getPaper() {
    return paper;
}

export type PaperGroup = paper.Group;

export function initPaper(canvasId: string) {
    paper.setup(canvasId);
    const element = document.getElementById(canvasId);

    // next part is from here:
    // ref:https://codepen.io/hichem147/pen/dExxNK<- thank you...

    // Create a simple drawing tool:
    const tool = new paper.Tool();

    // Define a mousedown and mousedrag handler
    tool.onMouseDown = function () {
        // not needed atm
    };

    tool.onMouseDrag = function (event: any) {
        const pan_offset = event.point.subtract(event.downPoint);
        paper.view.center = paper.view.center.subtract(pan_offset);
    };

    tool.onMouseUp = function () {
        // not needed atm
    };

    element?.addEventListener("mousewheel", function (event: any) {
        const paper = getPaper();
        let newZoom = paper.view.zoom;
        const oldZoom = paper.view.zoom;

        if (event.deltaY < 0) {
            newZoom = paper.view.zoom * 1.05;
        } else {
            newZoom = paper.view.zoom * 0.95;
        }

        const beta = oldZoom / newZoom;

        const mousePosition = new paper.Point(event.offsetX, event.offsetY);

        const viewPosition = paper.view.viewToProject(mousePosition);

        const mpos = viewPosition;
        const ctr = paper.view.center;

        const pc = mpos.subtract(ctr);
        const offset = mpos.subtract(pc.multiply(beta)).subtract(ctr);

        paper.view.zoom = newZoom;
        paper.view.center = paper.view.center.add(offset);

        event.preventDefault();
        paper.view.update();
    });
}
