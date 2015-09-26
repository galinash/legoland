#!/usr/bin/python
#
# Copyright (c) 2015 Galina Shubina
#
# This program computes optimal circular section out of Legos given diameter.
#
# Diameter is given in special units, such that the smallest standard lego
# unit ("a pip") is 5 long and 2 high. Please note that this is a fitting
# a "standing circle" rather than a horizontal circle (thus the height of
# a standard piece is important.
#
# Error is computed is a sum of all uncovered parts of the disk (i.e. contents
# of the circle in the mathematical sense) plus all parts of Legos outside
# the disk.
#
# The output of the program is an html snippet viewable in svg-enabled browser.
# A number of solutions is displayed (or made possible with code, if you tinker
# with it)
#   - UNALIGNED solutions: solutions that don't require that Lego pips stack
#                          evenly on top of one another (note that there are
#                          Lego pieces that could allow you change of alignment
#                          and thus circles with better error in some cases)
#   - ALIGNED solutions: solutions that require that Lego pips stack properly
#   - solutions WITH MIDDLE ROW: i.e. you can't cleanly split this circle into
#                                two half-circles or
#   - solutions WITHOUT THE MIDDLE ROW
#   - solutions CIRCUMSCRIBED by the circle: i.e. all pieces are entirely
#                                included within the circle of given diameter
#   - solutions UNCIRCUMSCRIBED by the circle
#     (note that clearly allowing for solutions to stray outside the circle
#      would commonly yield better error)

import sys
from math import acos, pow, sqrt, floor
from operator import itemgetter

class FunnyCircle:
    def __init__(self, diameter):
        self._diameter = float(diameter)

    def UnrestrictedFit(self, y, piece_height):
        """ y is location vertically above which we want to fit a piece of height h.
        For now, assume that we're not restricted by pip placement.

        Return width of the piece."""
        return 2 * sqrt(pow(self._diameter/2.0, 2) - pow(y + piece_height, 2))

    def UnrestrictedFitByPieceWidth(self, y, piece_height, piece_unit_width,
                                    align_pips, align_even_number,
                                    consider_outside):
        """ y is location vertically above which we want to fit a piece of height h.
        For now, assume that we're not restricted by pip placement.

        Return width of the piece and error area. Must be multiples of piece_width"""
        uw = self.UnrestrictedFit(y, piece_height)
        uw_min = uw - uw % piece_unit_width  # could be float division error below?

        width_in_pips = int(floor(uw_min/float(piece_unit_width)))
        if align_pips:
            if ((align_even_number and not width_in_pips%2) or
                ((not align_even_number) and width_in_pips%2)):
                pass
            else:
                if width_in_pips:
                    width_in_pips -= 1
                    uw_min = uw_min - piece_unit_width

        if consider_outside:
            in_error = self.ComputeSliceError(y, piece_height, uw_min)
            uw_min = self.ConsiderOutsidePieces(
                y, piece_height, piece_unit_width, in_error, uw_min,
                align_pips, align_even_number)
                
        return uw_min

    
    def ConsiderOutsidePieces(self, y, piece_height, piece_unit_width, in_best_error,
                              in_best_width, align_pips, align_even_number):
        """ Return new error-optimizing width. 

        1. there are no pieces in the minimum - this is the top or bottom row.
        1.a. unaligned
        1.b. aligned pips, 
        1.b.x. if odd, start with one, 
        1.b.y. if even start with two
        after figuring out the initial setup, keep adding two pieces
        """
        uw_min = in_best_width
        out_error = 0.0
        current_min = uw_min
        start = False
        if not uw_min:
            start = True
        best_error = in_best_error

        while True:
            try_extra = 0
            if start:
                try_extra = piece_unit_width
                if align_pips and align_even_number:
                    try_extra += piece_unit_width
            else:
                if align_pips:
                    try_extra = 2 * piece_unit_width
                else:
                    try_extra = piece_unit_width

            out_error = self.ComputeSliceError(y, piece_height, current_min + try_extra)
            if out_error < best_error:
                current_min += try_extra
                best_error = out_error
            else:
                break
            start = False
        return current_min

    
    def UnrestrictedFitHalf(self, piece_height, piece_width, vertical_offset=0,
                            align_pips=False, align_even_number=True,
                            consider_outside=False):
        """ Compute the widths of slices going up from offset (so we can deal with
        cases where we don't split down the middle). 

        vertical_offset - allow one to start with half the height of the piece, and
        so later insert a middle piece along the center of the the circle.

        align_pips - make it so only standard Lego pieces can be used
        align_even_number - the first piece should have an even number of "pips"

        consider_outside - whether to allow placing pieces partly outside the circle

        Returns array with y and width pairs."""
        y = vertical_offset
        widths_of_pieces = []
        last_width = 0
        
        while y + piece_height <= self._diameter/2.0:
            last_width = self.UnrestrictedFitByPieceWidth(
                y, piece_height, piece_width, align_pips, align_even_number,
                consider_outside)
            widths_of_pieces.append((y, last_width))
            y += piece_height
        if last_width:
            widths_of_pieces.append((y, 0.0))
        return widths_of_pieces

    def FitCircleSplitMiddle(self, piece_height, piece_width,
                             align_pips=False, align_even_number=True,
                             consider_outside=False):
        widths_of_pieces = self.UnrestrictedFitHalf(
            piece_height, piece_width, 0, align_pips, align_even_number,
            consider_outside)
        error = 2 * self.ComputeError(widths_of_pieces, piece_height)
        return (widths_of_pieces, 0, error)

    def FitCircleOffsetMiddleHalfPiece(self, piece_height, piece_width,
                                       align_pips=False, align_even_number=True,
                                       consider_outside=False):
        widths_of_pieces = self.UnrestrictedFitHalf(
            piece_height, piece_width, piece_height/2, align_pips, align_even_number,
            consider_outside)
        middle_piece_width = self.UnrestrictedFitByPieceWidth(
            0, piece_height/2, piece_width, align_pips, align_even_number,
            consider_outside)
        error = 2 * self.ComputeError(widths_of_pieces, piece_height)
        error += 2 * self.ComputeSliceError(0, piece_height/2, piece_width)
        return (widths_of_pieces, middle_piece_width, error)

    def ComputeSliceError(self, y, piece_height, piece_width):
        """ Compute area of the circle outside the width of the slice."""
        h = float(piece_height)
        w = float(piece_width)
        r = self._diameter/2.0
        r2 = r * r
        yh = y + h
        if piece_width:
            return (abs(acos(y/r) * r2 - acos(yh/r) * r2  - y * sqrt(r2 - y*y)
                        + yh * sqrt(r2 - yh*yh) - w * h))
        else:
            return acos(y/r) * r2  - y * sqrt(r2 - y*y)
            
    def ComputeError(self, widths_of_pieces, piece_height):
        return sum([self.ComputeSliceError(y, piece_height, w) for (y, w)
                    in widths_of_pieces])


class SVGMaker:
    
    @staticmethod
    def MakeSVGHeader(w, h):
        return ('<html><script src="http://d3js.org/d3.v3.min.js"></script><body>'
                '<svg width="%d" height="%d">' % (w, h))

    @staticmethod
    def MakeSVGFooter():
        return '</svg></body></html>'

    @staticmethod
    def MakeSVGCircle(x, y, r, style):
        return '<circle cx="%d" cy="%d" r="%f" style="%s"></circle>' % (x,y,r,style)

    @staticmethod
    def MakeSVGLegoPiece(w, h, ox, oy, y, piece_unit_width):
        """ w,h - width and height; ox,oy - origin of the circle, y - vertical
        offset from oy. """
        to_return = ''
        for i in range(1, int(w/piece_unit_width)):
            to_return += ('<line x1="%d" y1="%d" x2="%d" y2="%d" style="stroke:black;'
                          'stroke-width:1" />\n') % (
                              ox-w/2 + i*piece_unit_width, oy+y,
                              ox-w/2 + i*piece_unit_width, oy+y+h)
        to_return += ('<rect x="%d" y="%d" width="%d" height="%d" stroke="blue" '
                      'fill="none" />' % (ox-w/2, oy+y, w, h))
        return to_return
    
    @staticmethod
    def MakeSVGSnippetForCircleWithPieces(
            diameter, widths_of_pieces, error, middle_piece_width,
            piece_height, scale=5, piece_unit_width=5):
        canvas_width = diameter*scale + 20
        canvas_height = diameter*scale + 20
        piece_unit_width = 5*scale
        ox = canvas_width/2
        oy = canvas_height/2
        to_return = ''
        to_return += 'Error: %f <br clear="all"/>' % error
        to_return += SVGMaker.MakeSVGHeader(canvas_width, canvas_height)
        to_return += '\n'
        to_return += SVGMaker.MakeSVGCircle(ox, oy, diameter*scale/2,
                                            'fill:none;stroke:black;')
        to_return += '\n'
        for (y, last_width) in widths_of_pieces:
            if last_width:
                to_return += SVGMaker.MakeSVGLegoPiece(
                    last_width*scale, piece_height*scale,
                    ox, oy, y*scale, piece_unit_width)
                to_return += '\n'
                to_return += SVGMaker.MakeSVGLegoPiece(
                    last_width*scale, piece_height*scale,
                    ox, oy, (-y-piece_height)*scale, piece_unit_width)
                to_return += '\n'
        if middle_piece_width:
            to_return += SVGMaker.MakeSVGLegoPiece(
                middle_piece_width*scale, piece_height*scale,
                ox, oy, (-piece_height/2)*scale, piece_unit_width)
            to_return += '\n'
        to_return += SVGMaker.MakeSVGFooter()
        to_return += '\n'
        return to_return

    
def FitCircle(diameter, piece_height=2, pip_width=5, consider_outside=True):
    diameter = float(diameter)
    circle = FunnyCircle(diameter)
    widths_middles_errors_align = [
        (circle.FitCircleSplitMiddle(
            piece_height, pip_width, False, False, consider_outside), False),
        (circle.FitCircleOffsetMiddleHalfPiece(
            piece_height, pip_width, False, False, consider_outside), False),
        (circle.FitCircleSplitMiddle(
            piece_height, pip_width, True, True, consider_outside), True),
        (circle.FitCircleOffsetMiddleHalfPiece(
            piece_height, pip_width, True, True, consider_outside), True),
        (circle.FitCircleSplitMiddle(
            piece_height, pip_width, True, False, consider_outside), True),
        (circle.FitCircleOffsetMiddleHalfPiece(
            piece_height, pip_width, True, False, consider_outside), True)]

    # find the best fit among the aligned and unaligned solutions
    (min_index_align, min_err_align) = min(
        enumerate([e for ((w, m, e), a) in widths_middles_errors_align if a]),
        key=itemgetter(1))
    (min_index_unalign, min_err_unalign) = min(
        enumerate([e for ((w, m, e), a) in widths_middles_errors_align if not a]),
        key=itemgetter(1))

    print "Best aligned error %f<br/>Best unligned error %f<br/>" % (
        min_err_align, min_err_unalign)

    for ((w, m, e), a) in widths_middles_errors_align:
        print SVGMaker.MakeSVGSnippetForCircleWithPieces(
            diameter, w, e, m, piece_height, scale=3)
        print '<br clear="all">'
    
    
def main():
    # unit length given in the argument is assuming there are 5 "units"
    # between two lego pips
    if len(sys.argv) == 1 or not sys.argv[1]:
        print "Please enter diameter as the first argument."
        return
    FitCircle(sys.argv[1])    


if __name__ == "__main__":
    main()
