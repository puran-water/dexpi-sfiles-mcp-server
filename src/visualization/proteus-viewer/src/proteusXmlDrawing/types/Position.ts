import { Axis } from "./Axis";
import { Component } from "../Component";
import { Location } from "./Location";
import { Reference } from "./Reference";

/**
 * This defines the place where an items origin is on a P&ID drawing.
 * This is in effect the location of the items symbol.
 * The Axis and Reference attributes are used to define the coordinate orientation in 3D space
 * The drawing is considered to be on the plane of Z=0.
 * All geometries in a P&ID file are accompanied by Axis and Reference elements.  These define rotations around 3 dimensional axis that define how to map the coordinates defined for the item into the target environment.  For most 2D drawing work the following values give the expected behaviour (i.e. the coordinates are defined in the 2D drawing plane).
 *
 * <Axis X="0" Y="0" Z="1"/>
 * <Reference X="1" Y="0" Z="0"/>
 * Some curve primitives such as ellipses in XMpLant require more complex use of Axis and Reference in order to define the 2D forms.
 *
 * The <Axis> value defines a unit vector in 3D space about which an object should rotate.  For 2D diagrams nearly all geometries will define this element as <Axis X="0" Y="0" Z="1"/> which denotes a vector aligned with the Z-axis.
 *
 * The <Reference> element defines what is effectively the rotation about the <Axis> element. When you see the value written as <Reference X="1" Y="0" Z="0"/> it indicates that the X-Axis with which the object’s points are defined use the same X-Axis on the output surface/window with which to orientate – in other words no rotation is required when you have the following paired elements;
 *
 * <Axis X="0" Y="0" Z="1"/>
 * <Reference X="1" Y="0" Z="0"/>
 *
 * Common variations include :-
 *
 * Inverted z axis (flip around y axis) : <Axis X="0" Y="0" Z="-1"/>
 *
 * Rotation about the origin :  <Reference X=”[cosØ]” Y=”[sinØ]” Z=”0” />
 *
 * Where :-
 *
 * [sinØ] – is the sine of the rotation angle
 * [cosØ] – is the cosine of the rotation angle
 * The rotation is measured anti-clockwise
 *
 */
export type Position = PositionClass & Component;

type PositionClass = {
    Axis: Axis[];
    Reference: Reference[];
    Location: Location[];
};
