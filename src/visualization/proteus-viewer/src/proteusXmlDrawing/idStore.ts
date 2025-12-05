import { Component } from "./Component";

const idStore = new Map<string, Component>();

export function clearStore() {
    idStore.clear();
}

export function getStore() {
    return idStore;
}

export function addToIdStore(id: string, obj: Component) {
    if (idStore.has(id)) {
        console.warn("duplicate ID's in file", id);
        console.warn("prev", idStore.get(id));
        console.warn("new", obj);
    }
    idStore.set(id, obj);
}

export function getFromIdStore(componentName: string) {
    return idStore.get(componentName) || null;
}
