# coding: utf-8

# Copyright (C) 2016, 2017, S. J. Baugh

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

# Works with Python >= 3.7 and Qt5

from __future__ import division

import math

# PyQt interface imports
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class NotAGraphError(ValueError):
    """Exception thrown by reCreateGraph."""
    pass


class Graph(object):
    """A graph object for use with Python Qt based programs.

        Usage:

        Create a label.

        Create the Graph object passing the label and other arguments
        to it.

        Call add_text method(s) to position any text.

        Optionally call the draw method with no arguments to show the
        Graph grid and text only.

        Call draw method with any number of line arguments
        (as lists of points) to show the line(s) on the Graph and the text.
        See the draw method below.
        """

    def __init__(self, graph_label,
                 xmin=0, xmax=1000,
                 ymin=0, ymax=1000,
                 xgrids=10, ygrids=10,
                 size_x=500, size_y=500,
                 show_labels=(True, True),
                 text_pixel_size=12,
                 background=QColor(234, 255, 202)):

        """ Initialises the Graph object.

            graph_label is the label control on to which the Graph is
            rendered as a QPixmap.

            xmax and ymax are the maximum values in the x and y directions.
            xmin and ymin are the minimum values in the x and y directions.

            xgrids and ygrids are the number of grid lines in the
            x and y directions, the top or right of the graph is
            considered a grid line.

            text_pixel_size determines the size of the grid labels and
            any text.

            size_x and size_y are the pixel size of the pixmap that
            the Graph is drawn on. These set the dimensions of the label.
            """

        # Save the instance attributes
        self.graph_label = graph_label
        self.image_size_x = size_x
        self.image_size_y = size_y
        self.show_labels_x = show_labels[0]
        self.show_labels_y = show_labels[1]
        self.pixel_size = text_pixel_size

        self.xmin = xmin
        self.ymin = ymin
        self.background = background

        self.texts = []
        self.polarTexts = []  # only used in Polar variants
        self.centreMax = True  # only used in Polar variants

        self.lines = []

        self.graph_image = None

        # avoid division by zero errors:

        if xmax - xmin == 0:
            self.xmax = 1
            self.xmin = 0
        else:
            self.xmax = xmax

        if ymax - ymin == 0:
            if ymax > 0:
                self.ymax = ymax
                self.ymin = 0
            else:
                self.ymax = 0
                self.ymin = ymin
        else:
            self.ymax = ymax

        if xgrids <= 0:
            self.xgrids = 1
        else:
            self.xgrids = xgrids

        if ygrids <= 0:
            self.ygrids = 1
        else:
            self.ygrids = ygrids

        # Default format for grid axies number labels
        self.xformat = '{}'
        self.yformat = '{}'

    def tx(self, x):

        """Translate x value in graph coordinates to the image coordinates
            based on the image size, xmin and xmax.

            returns the x value in image coordinates as a float."""

        xt = (float(self.image_size_x) / float(self.xmax - self.xmin) *
              (x - self.xmin))

        return xt

    def ty(self, y):

        """Translate y value in graph coordinates to the image coordinates
            based on the image size, ymin and ymax.

            returns the y value in image coordinates as a float."""

        imsize = self.image_size_y

        yt = (float(imsize) / float(self.ymax - self.ymin) *
              (y - self.ymin))

        yyt = imsize - yt

        return yyt

    def _grid_and_texts(self):

        """Draws the grids, grid labels and any texts on
            pixmap: self.graph_image.

            Private method called by the (sub-classed) draw methods.
            Do not call this method directly."""

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # set the font pixel size
        new_font = QFont(painter.font())  # get a copy of the old font
        new_font.setPixelSize(self.pixel_size)
        painter.setFont(new_font)  # update the font

        # get the metrics of the new font
        metrics = painter.fontMetrics()

        # draw grids at intervals

        # x grids
        for xi in range(self.xgrids):
            xg = int(float(self.image_size_x) / float(self.xgrids) * xi)

            painter.setPen(QColor('# 89a0cd'))
            move_to = QPoint(xg, 0)
            line_to = QPoint(xg, self.image_size_y)
            painter.drawLine(move_to, line_to)

            if self.show_labels_x:
                if (xi != 0):  # or (self.xmin == self.ymin):
                    painter.setPen(Qt.blue)

                    painter.drawText(xg + 2, self.image_size_y - 4,
                                     self.xformat.format(
                                         float(self.xmin) + float(self.xmax - self.xmin)
                                         / float(self.xgrids) * xi)
                                     )

        # first x axis label:

        # get pixel width and height of the text
        fm = metrics.boundingRect(self.xformat.format(float(self.xmin)))
        wx = fm.width()
        hy = fm.height()

        if self.show_labels_x:
            # draw at pixel width (+ a bit) back from the right of the image
            # and pixel height (+ a bit) up from the bottom
            painter.drawText(4,
                             self.image_size_y - 4 - hy,
                             self.xformat.format(float(self.xmin)))

        # final x axis label:

        # get pixel width and height of the text
        fm = metrics.boundingRect(self.xformat.format(float(self.xmax)))
        wx = fm.width()
        hy = fm.height()

        if self.show_labels_x:
            # draw at pixel width (+ a bit) back from the right of the image
            # and pixel height (+ a bit) up from the bottom
            painter.drawText(self.image_size_x - wx - 4,
                             self.image_size_y - 4 - hy,
                             self.xformat.format(float(self.xmax)))

        # y grids
        for yi in range(self.ygrids):
            yg = int(float(self.image_size_y) / float(self.ygrids) * yi)

            painter.setPen(QColor('#89a0cd'))
            move_to = QPoint(0, yg)
            line_to = QPoint(self.image_size_x, yg)
            painter.drawLine(move_to, line_to)

            if self.show_labels_y:
                # draw y axis labels other than first/final labels
                if yi != 0:
                    painter.setPen(Qt.red)
                    painter.drawText(4, yg - 2, self.yformat.format(self.ymax -
                                                                    ((float(self.ymax - self.ymin) /
                                                                      float(self.ygrids) * yi))))

        # first y axis label:

        # get pixel height of the text
        hy = metrics.boundingRect(self.yformat.format(
            float(self.ymax))).height()

        if self.show_labels_y:
            # draw at pixel height from the top of the image
            painter.drawText(4, self.image_size_y - 4, self.yformat.format(float(self.ymin)))

        # final y axis label:

        # get pixel height of the text
        hy = metrics.boundingRect(self.yformat.format(
            float(self.ymax))).height()

        if self.show_labels_y:
            # draw at pixel height from the top of the image
            painter.drawText(4, hy - 2, self.yformat.format(float(self.ymax)))

        # draw borders with a Rect
        painter.setPen(Qt.blue)
        painter.drawRect(0, 0, self.image_size_x - 1,
                         self.image_size_y - 1)

        # draw texts(if any)
        for t in self.texts:
            painter.setPen(QColor(t[3]))
            painter.drawText(self.tx(t[1]), self.ty(t[2]), t[0])

        painter.end()

        # self.update()

    def draw(self, *args):

        """Draw the graph on the pixmap of a label.

            The arguments are lines to be drawn as lists of points.
            Points are a tuple, or other sequence:
            (x, y) or (x, y, 'colour') or  (x, y, 'colour', point_size)
            or  (x, y, 'colour', point_size, text)

            If the colour is not given the point is drawn in the
            default colour. The colour may be be any string that may be
            passed to QColor, such as a name like 'red' or
            a hex value such as '#F0F0F0'.

            If a point_size is given, a rectange of that size will be drawn
            at the start of that line segment, a colour must be given.

            Any number of line arguments may be given, each drawn as a
            separate line.

            The draw method may be called multiple times. Each time old
            lines are removed and the new line argument(s) are drawn along
            with any text.

            Attribute `lines` contains the list of the lines passed as arguments.
            """

        # Save the arguments
        self.lines = args[:]

        # create the image as a pixmap
        self.graph_image = QPixmap(self.image_size_x, self.image_size_y)
        self.graph_image.fill(self.background)

        self._grid_and_texts()  # draw the grids and texts

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # set the font pixel size
        new_font = QFont(painter.font())  # get a copy of the old font
        new_font.setPixelSize(self.pixel_size)
        painter.setFont(new_font)  # update the font

        # draw the lines (if any):

        # draw as individual lines so each can be a different colour
        for line in args:

            for i, point in enumerate(line):

                # if a colour is passed, use it
                if len(point) >= 3:  # if point has a colour field
                    painter.setPen(QColor(point[2]))
                    painter.setBrush(QColor(point[2]))
                else:
                    painter.setPen(Qt.black)  # default colour

                if i == 0:
                    # first point is a move
                    last_point = QPoint(self.tx(point[0]),
                                        self.ty(point[1]))

                    if len(point) >= 4:  # if point has a point size field
                        # draw a rectangle at start of point
                        point_size = point[3]
                        painter.drawRect(
                            self.tx(point[0]) - point_size // 2,
                            self.ty(point[1]) - point_size // 2,
                            point_size, point_size)

                    if len(point) >= 5:  # if point has a text field
                        painter.drawText(self.tx(point[0]), self.ty(point[1]), point[4])

                else:
                    # subsequent points
                    if len(point) >= 4:  # if point has a point size field
                        # draw a rectangle at the point
                        point_size = point[3]
                        painter.drawRect(
                            self.tx(point[0]) - point_size // 2,
                            self.ty(point[1]) - point_size // 2,
                            point_size, point_size)

                    if len(point) >= 5:  # if point has a text field
                        painter.drawText(self.tx(point[0]), self.ty(point[1]), point[4])

                    # draw the line
                    line_to = QPoint(self.tx(point[0]), self.ty(point[1]))
                    painter.drawLine(last_point, line_to)

                    # update last point
                    last_point = QPoint(self.tx(point[0]),
                                        self.ty(point[1]))

        painter.end()
        self.graph_label.setPixmap(self.graph_image)

    def add_text(self, text, x, y, colour='black', fixed=False):

        """`text` is added to the graph at x, y (in graph coordinates)
            in the specified colour and using the default typeface.
            Argument text_pixel_size passed in the initialisation
            determines the font size.

            If `fixed` is True the text is not removed by clear_texts.
            This is useful for axis and other annotations that will not change.

            Any number of texts can be added by multiple calls to
            this method.

            The text is displayed after the next call to the draw method.
            """

        self.texts.append((text, x, y, colour, fixed))

    def remove_text(self, text, x, y, colour='black', fixed=False):

        """text at x, y (in graph coordinates) in the specified colour is
             removed from the Graph.

            Multiple texts can be removed by multiple calls to this method.

            The updated Graph is displayed after the next call
            to the draw method.

            Raises exception ValueError if the text, x, y, colour, fixed
            combination is not found."""

        inx = self.texts.index((text, x, y, colour, fixed))  # find the text
        del self.texts[inx]  # delete it from the list

    def add_text_by_proportion(self, text, x_proportion, y_proportion, colour='black', fixed=False):

        """param: text is added to the graph at x_proportion, y_proportion
            in proportions, from 0.0 to 1.0, of the x and y sizes of the graph,
            in the specified colour and using the default typeface.
            Argument text_pixel_size passed in the initialisation
            determines the font size.

            Any number of texts can be added by multiple calls to
            this method.

            The text is displayed after the next call to the draw method.
            """

        self.add_text(text,
                      (self.xmax - self.xmin) * x_proportion + self.xmin,
                      (self.ymax - self.ymin) * y_proportion + self.ymin,
                      colour, fixed)

    def remove_text_by_proportion(self, text, x_proportion, y_proportion, colour='black', fixed=False):

        """text at x_proportion, y_proportion in proportions,
            from 0.0 to 1.0, of the x and y sizes of the graph,
            in the specified colour is removed from the Graph.

            Multiple texts can be removed by multiple calls to this method.

            The updated Graph is displayed after the next call
            to the draw method.

            Raises exception ValueError if the text, x_proportion, y_proportion, colour
            combination is not found."""

        self.remove_text(text,
                         (self.xmax - self.xmin) * x_proportion + self.xmin,
                         (self.ymax - self.ymin) * y_proportion + self.ymin,
                         colour, fixed)

    def clear_texts(self):

        """All (non-polar) texts are removed from the Graph that do not have
            `fixed` set.

            The updated Graph is displayed after the next call
            to the draw method."""

        for t in self.texts[:]:
            if not t[4]:
                self.texts.remove(t)

    def get_image(self):

        """Returns the graph as an image.

            Returns None if no graph has been drawn."""

        if self.graph_image:
            return self.graph_image.toImage()
        else:
            return None

    def save_image(self, filename):

        """Saves the graph as an image in file: filename.

            The image type is inferred from the file extension.

            No image is saved if no graph has been drawn or the image
            cannot be created.

            Returns True if it was saved correctly,
            False if it could not be saved
            or None if there is no valid image to save."""

        image = self.get_image()
        if image:
            saved = image.save(filename, None, -1)  # default resolution
            return saved
        return None

    def set_grid_label_format(self, x='{}', y='{}'):

        """Set the format of the numbers labelling the X and Y grid axies.

            The strings should be a Python string format method value,
            should be appropriate for a float variable
            and should include the braces.

            The new format is displayed after the next call to the
            draw method.

            e.g.  '{:0.2f}'

          """

        self.xformat = x
        self.yformat = y


class Scatter(Graph):
    """A scatter graph object for use with Python Qt based programs.

        Usage:

        Create a label.

        Create the Scatter object passing the label and other arguments.

        Call add_text method(s) inherited from Graph to position any text.
        Optionally call the draw method with no arguments to show the
        grid and text only.

        Call draw method with any number of scatter arguments
        (as lists of points) to show the point(s) on the Scatter graph
        and the text. See the draw method below.

        Other methods as for the Graph object.
        """

    def draw(self, *args):

        """Draw the scatter graph on the pixmap of a label.

            The arguments are square points to be drawn as lists of points.
            Points are a tuple, or other sequence:
            (x, y) or (x, y, 'colour') or (x, y, 'colour', size)
            or  (x, y, 'colour', point_size, text)

            If the colour is not given the point is drawn in the default
            colour.

            The default size is 2.

            Any number of  arguments may be given, each drawn as a
            separate set of points.

            The draw method may be called multiple times. Each time old
            points are removed and the new list of points argument(s) are
            drawn along with any text.

            Attribute `lines` contains the list of the lines passed as arguments.
            """

        # Save the arguments
        self.lines = args[:]

        # create the image as a pixmap
        self.graph_image = QPixmap(self.image_size_x, self.image_size_y)
        self.graph_image.fill(self.background)

        self._grid_and_texts()  # draw the grids and texts

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # set the font pixel size
        new_font = QFont(painter.font())  # get a copy of the old font
        new_font.setPixelSize(self.pixel_size)
        painter.setFont(new_font)  # update the font

        # draw the scatter points (if any):

        # draw as individual points so each can be a different colour
        for line in args:

            for point in line:

                # draw points as rectangles

                # if a colour is passed, use it
                if len(point) >= 3:
                    painter.setBrush(QColor(point[2]))
                    painter.setPen(QColor(point[2]))
                else:
                    painter.setBrush(Qt.black)  # default colour
                    painter.setPen(Qt.black)

                if len(point) >= 4:  # if a point size has been given
                    point_size = point[3]
                else:
                    point_size = 2

                if len(point) >= 5:  # if point has a text field
                    painter.drawText(self.tx(point[0]), self.ty(point[1]), point[4])

                # draw a rectangle at the point
                painter.drawRect(self.tx(point[0]) - point_size // 2,
                                 self.ty(point[1]) - point_size // 2,
                                 point_size, point_size)

        painter.end()
        self.graph_label.setPixmap(self.graph_image)


class Poly(Graph):
    """A graph object for use with Python Qt based programs. Draws the
        graph lines as poly lines to improve performance over the Graph
        object, but with reduced draw options.

        Usage:

        Create a label.

        Create the Poly object passing the label and other arguments.

        Call add_text method(s) inherited from Graph to position any text.
        Optionally call the draw method with no arguments to show the grid
        and text only.

        Call draw method with any number of line arguments
        (as lists of points) to show the point(s) on the Poly graph
        and the text. See the draw method below.

        Other methods as for the Graph object.
        """

    def draw(self, *args):

        """Draw the graph on the pixmap of a label.

            The arguments are lines to be drawn as lists of points.
            Points are a tuple, or other sequence:
            (x, y) or (x, y, 'colour') or  (x, y, 'colour', point_size)
            or  (x, y, 'colour', point_size, text)

            If the colour is not given the line is drawn in the
            default colour. The colour may be be any string that may be
            passed to QColor, such as a name like 'red' or
            a hex value such as '#F0F0F0'.

            The colour for the first point (if given) is used as the
            colour for the whole line. Any other colour parameters are
            ignored.

            Any point_size or text parameters with points are ignored.

            Any number of line arguments may be given, each drawn as a
            separate poly line.

            The draw method may be called multiple times. Each time old
            lines are removed and the new line argument(s) are drawn along
            with any text.

            Attribute `lines` contains the list of the lines passed as arguments."""

        # Save the arguments
        self.lines = args[:]

        # create the image as a pixmap
        self.graph_image = QPixmap(self.image_size_x, self.image_size_y)
        self.graph_image.fill(self.background)

        self._grid_and_texts()  # draw the grids and texts

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # draw the lines (if any):

        # draw lines using a QPainterPath to speed up rendering
        for line in args:
            # Create a QPainterPath
            path = QPainterPath()

            for i, point in enumerate(line):

                if i == 0:
                    # if a colour is passed, use it
                    if len(point) >= 3:  # if point has a colour field
                        painter.setPen(QColor(point[2]))
                    else:
                        painter.setPen(Qt.black)  # default colour

                    # first point is a move
                    path.moveTo(self.tx(point[0]),
                                self.ty(point[1]))

                else:
                    # subsequent points

                    # draw the line
                    path.lineTo(self.tx(point[0]), self.ty(point[1]))

            painter.drawPath(path)

        painter.end()
        self.graph_label.setPixmap(self.graph_image)


class Polar(Graph):
    """A graph object for use with Python Qt based programs.

        Usage:

        Create a label.

        Create the Polar object passing the label and other arguments.

        Call add_text method(s) inherited from Graph to position any text.
        Optionally call the draw method with no arguments to show the grid
        and text only.

        Call draw method with any number of line arguments
        (as lists of points) to show the point(s) on the Polar graph
        and the text. See the draw method below.

        Other methods as for the Graph object.

        """

    def __init__(self, graph_label,
                 r_min=0, r_max=90,
                 theta_min=0, theta_max=360,
                 r_circles=6, theta_spokes=12,
                 size_x=500, size_y=500,
                 show_labels=(True, True),
                 text_pixel_size=12,
                 background=QColor(234, 255, 202)):

        """ Initialises the Polar graph object.

            graph_label is the label control on to which the Graph is
            rendered as a QPixmap.

            r_max and theta_max are the maximum values in the r and theta directions.
            r_min and theta_min are the minimum values in the r and theta directions.

            r_circles and theta_spokes are the number of grid lines.

            text_pixel_size determines the size of the grid labels and
            any text.

            size_x and size_y are the pixel size of the pixmap that
            the Graph is drawn on. These set the dimensions of the label.
            """

        # Save the instance attributes
        self.graph_label = graph_label
        self.image_size_x = size_x
        self.image_size_y = size_y
        self.show_labels_x = show_labels[0]
        self.show_labels_y = show_labels[1]
        self.pixel_size = text_pixel_size
        self.xmin = r_min
        self.ymin = theta_min
        self.background = background

        self.texts = []
        self.polarTexts = []
        self.centreMax = True  # for future use

        self.lines = []

        self.graph_image = None

        # avoid division by zero errors:

        if r_max - r_min == 0:
            self.xmax = 1
            self.xmin = 0
        else:
            self.xmax = r_max

        if theta_max - theta_min == 0:
            if theta_max > 0:
                self.ymax = theta_max
                self.ymin = 0
            else:
                self.ymax = 0
                self.ymin = theta_min
        else:
            self.ymax = theta_max

        if r_circles <= 0:
            self.xgrids = 1
        else:
            self.xgrids = r_circles

        if theta_spokes <= 0:
            self.ygrids = 1
        else:
            self.ygrids = theta_spokes

        # Default format for grid axies number labels
        self.xformat = '{}'
        self.yformat = '{}'

    def draw(self, *args):

        """Draw the graph on the pixmap of a label.

            The arguments are lines to be drawn as lists of points.
            Points are a tuple, or other sequence:
            (r, theta) or (r, theta, 'colour') or (r, theta, 'colour', point_size)
            or (r, theta, 'colour', point_size, text)

            theta is in radians

            If the colour is not given the point is drawn in the
            default colour. The colour may be be any string that may be
            passed to QColor, such as a name like 'red' or
            a hex value such as '#F0F0F0'.

            If a point_size is given, a rectange of that size will be drawn
            at the start of that line segment, a colour must be given.

            Any number of line arguments may be given, each drawn as a
            separate line.

            The draw method may be called multiple times. Each time old
            lines are removed and the new line argument(s) are drawn along
            with any text.

            Attribute `lines` contains the list of the lines passed as arguments.
            """

        # Save the arguments
        self.lines = args[:]

        # create the image as a pixmap
        self.graph_image = QPixmap(self.image_size_x, self.image_size_y)
        self.graph_image.fill(self.background)

        self._grid_and_texts()  # draw the grids and texts

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # set the font pixel size
        new_font = QFont(painter.font())  # get a copy of the old font
        new_font.setPixelSize(self.pixel_size)
        painter.setFont(new_font)  # update the font

        # draw the lines (if any):

        # draw as individual lines so each can be a different colour
        for line in args:

            for i, point in enumerate(line):

                # if a colour is passed, use it
                if len(point) >= 3:  # if point has a colour field
                    painter.setPen(QColor(point[2]))
                    painter.setBrush(QColor(point[2]))
                else:
                    painter.setPen(Qt.black)  # default colour

                if i == 0:
                    # first point is a move
                    last_point = QPoint(self.pr(point[0], point[1]), self.pt(point[0], point[1]))

                    if len(point) >= 4:  # if point has a point size field
                        # draw a rectangle at start of point
                        point_size = point[3]
                        painter.drawRect(
                            self.pr(point[0], point[1]) - point_size // 2,
                            self.pt(point[0], point[1]) - point_size // 2,
                            point_size, point_size)

                    if len(point) >= 5:  # if point has a text field
                        painter.drawText(self.pr(point[0], point[1]), self.pt(point[0], point[1]), point[4])

                else:
                    # subsequent points
                    if len(point) >= 4:  # if point has a point size field
                        # draw a rectangle at the point
                        point_size = point[3]
                        painter.drawRect(
                            self.pr(point[0], point[1]) - point_size // 2,
                            self.pt(point[0], point[1]) - point_size // 2,
                            point_size, point_size)

                    if len(point) >= 5:  # if point has a text field
                        painter.drawText(self.pr(point[0], point[1]), self.pt(point[0], point[1]), point[4])

                    # draw the line
                    line_to = QPoint(self.pr(point[0], point[1]), self.pt(point[0], point[1]))
                    painter.drawLine(last_point, line_to)

                    # update last point
                    last_point = QPoint(self.pr(point[0], point[1]), self.pt(point[0], point[1]))

        painter.end()
        self.graph_label.setPixmap(self.graph_image)

    def pRad(self, r):

        """ radial value `r` as an inverse proportion of the polar graph radius."""

        graphRadius = min(self.image_size_x, self.image_size_y) / 2.0

        # r as inverse proportion
        rp = (self.xmax - r) / (self.xmax - self.xmin)

        rad = graphRadius * rp

        return rad

    def pr(self, r, theta):

        """Translate radial `r` and angle `theta` (radians) values in
            graph coordinates to the x image coordinate.

            returns the x value in image coordinates as a float."""

        centre = min(self.image_size_x, self.image_size_y) / 2.0

        x = centre + self.pRad(r) * math.sin(theta)

        return x

    def pt(self, r, theta):

        """Translate radial `r` and angle `theta` (radians) values in
            graph coordinates to the y image coordinate.

            returns the y value in image coordinates as a float."""

        centre = min(self.image_size_x, self.image_size_y) / 2.0

        y = centre - self.pRad(r) * math.cos(theta)

        return y

    def _grid_and_texts(self):

        """Draws the grids, grid labels and any texts on
            pixmap: self.graph_image.

            Private method called by the (sub-classed) draw methods.
            Do not call this method directly."""

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # set the font pixel size
        new_font = QFont(painter.font())  # get a copy of the old font
        new_font.setPixelSize(self.pixel_size)
        painter.setFont(new_font)  # update the font

        # get the metrics of the new font
        metrics = painter.fontMetrics()

        # draw grids at intervals

        # r grids (circles)
        for ri in range(self.xgrids + 1):
            centre = min(self.image_size_x, self.image_size_y) / 2.0

            radius = int(float(centre) / float(self.xgrids) * ri)

            painter.setPen(QColor('# 89a0cd'))
            centreP = QPointF(centre, centre)
            painter.drawEllipse(centreP, radius, radius)

            if self.show_labels_x:
                if (ri != 0):
                    painter.setPen(Qt.blue)

                    painter.drawText(radius + 2, centreP.x() - 4,
                                     self.xformat.format(
                                         float(self.xmin) + float(self.xmax - self.xmin)
                                         / float(self.xgrids) * ri)
                                     )

        # first x axis label:

        # get pixel width and height of the text
        fm = metrics.boundingRect(self.xformat.format(float(self.xmin)))
        wx = fm.width()
        hy = fm.height()

        if self.show_labels_x:
            # draw at pixel width (+ a bit) back from the right of the image
            # and pixel height (+ a bit) up from the bottom
            painter.drawText(4, centre - hy - 4, self.xformat.format(float(self.xmin)))

        # theta grids (radial lines)
        for yi in range(self.ygrids):
            yg = float(self.image_size_y) / float(self.ygrids) * yi

            painter.setPen(QColor('# 89a0cd'))
            move_to = QPoint(centre, centre)
            line_to = QPoint(centre - radius * math.sin(math.tau / self.ygrids * yi),
                             centre - radius * math.cos(math.tau / self.ygrids * yi))
            painter.drawLine(move_to, line_to)

            if self.show_labels_y:
                # draw y axis labels other than first/final labels
                if yi != 0:
                    painter.setPen(Qt.red)
                    painter.drawText(line_to.x() + 4, line_to.y() - 2,
                                     self.yformat.format(self.ymax -
                                                         ((float(self.ymax - self.ymin) /
                                                           float(self.ygrids) * yi))))

        # first theta grid label:

        # get pixel height of the text
        hy = metrics.boundingRect(self.yformat.format(
            float(self.ymax))).height()

        if self.show_labels_y:
            # draw at pixel height from the top of the image
            painter.drawText(centre + 4, hy, self.yformat.format(float(self.ymin)))

        # draw borders with a Rect
        painter.setPen(Qt.blue)
        painter.drawRect(0, 0, self.image_size_x - 1,
                         self.image_size_y - 1)

        # draw texts(if any)
        for t in self.texts:
            painter.setPen(QColor(t[3]))
            painter.drawText(self.tx(t[1]), self.ty(t[2]), t[0])

        for t in self.polarTexts:
            painter.setPen(QColor(t[3]))
            painter.drawText(self.pr(t[1], t[2]), self.pt(t[1], t[2]), t[0])

        painter.end()

    def add_polar_text(self, text, r, theta, colour='black', fixed=False):

        """param: text is added to the graph at r, theta (in graph coordinates)
            in the specified colour and using the default typeface.
            Argument text_pixel_size passed in the initialisation
            determines the font size.

            Any number of texts can be added by multiple calls to
            this method.

            If `fixed` is True the text is not removed by clear_polar_texts.
            This is useful for axis and other annotations that will not change.

            The text is displayed after the next call to the draw method.
            """

        self.polarTexts.append((text, r, theta, colour, fixed))

    def clear_polar_texts(self):

        """All polar texts are removed from the Graph that do not
            have `fixed` set.

            The updated Graph is displayed after the next call
            to the draw method."""

        for t in self.polarTexts[:]:
            if not t[4]:
                self.polarTexts.remove(t)

    def remove_polar_text(self, text, r, theta, colour='black', fixed=False):

        """text at r, theta (in graph coordinates) in the specified colour is
             removed from the Graph.

            Multiple texts can be removed by multiple calls to this method.

            The updated Graph is displayed after the next call
            to the draw method.

            Raises exception ValueError if the text, r, theta, colour, fixed
            combination is not found."""

        inx = self.polarTexts.index((text, r, theta, colour, fixed))  # find the text
        del self.polarTexts[inx]  # delete it from the list


class PolarScatter(Polar):
    """A polar scatter graph object for use with Python Qt based programs.

        Usage:

        Create a label.

        Create the Scatter object passing the label and other arguments.

        Call add_text method(s) inherited from Polar to position any text.
        Optionally call the draw method with no arguments to show the
        grid and text only.

        Call draw method with any number of scatter arguments
        (as lists of points) to show the point(s) on the Scatter graph
        and the text. See the draw method below.

        Other methods as for the Graph object.
        """

    def draw(self, *args):

        """Draw the scatter graph on the pixmap of a label.

            The arguments are square points to be drawn as lists of points.
            Points are a tuple, or other sequence:
            (r, theta) or (r, theta, 'colour') or  (r, theta, 'colour', point_size)
            or (r, theta, 'colour', point_size, text)

            theta is in radians

            If the colour is not given the point is drawn in the default
            colour.

            The default size is 2.

            Any number of  arguments may be given, each drawn as a
            separate set of points.

            The draw method may be called multiple times. Each time old
            points are removed and the new list of points argument(s) are
            drawn along with any text.

            Attribute `lines` contains the list of the lines passed as arguments.
            """

        # Save the arguments
        self.lines = args[:]

        # create the image as a pixmap
        self.graph_image = QPixmap(self.image_size_x, self.image_size_y)
        self.graph_image.fill(self.background)

        self._grid_and_texts()  # draw the grids and texts

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # set the font pixel size
        new_font = QFont(painter.font())  # get a copy of the old font
        new_font.setPixelSize(self.pixel_size)
        painter.setFont(new_font)  # update the font

        # draw the scatter points (if any):

        # draw as individual points so each can be a different colour
        for line in args:

            for point in line:

                # draw points as rectangles

                # if a colour is passed, use it
                if len(point) >= 3:
                    painter.setBrush(QColor(point[2]))
                    painter.setPen(QColor(point[2]))
                else:
                    painter.setBrush(Qt.black)  # default colour
                    painter.setPen(Qt.black)

                if len(point) >= 4:  # if a point size has been given
                    point_size = point[3]
                else:
                    point_size = 2

                if len(point) >= 5:  # if point has a text field
                    painter.drawText(self.pr(point[0], point[1]), self.pt(point[0], point[1]), point[4])

                # draw a rectangle at the point
                painter.drawRect(self.pr(point[0], point[1]) - point_size // 2,
                                 self.pt(point[0], point[1]) - point_size // 2,
                                 point_size, point_size)

        painter.end()
        self.graph_label.setPixmap(self.graph_image)


class PolarPoly(Polar):
    """A graph object for use with Python Qt based programs. Draws the
        graph lines as poly lines to improve performance over the Polar
        object, but with reduced draw options.

        Usage:

        Create a label.

        Create the Poly object passing the label and other arguments.

        Call add_text method(s) inherited from Graph to position any text.
        Optionally call the draw method with no arguments to show the grid
        and text only.

        Call draw method with any number of line arguments
        (as lists of points) to show the point(s) on the Poly graph
        and the text. See the draw method below.

        Other methods as for the Graph object.
        """

    def draw(self, *args):

        """Draw the graph on the pixmap of a label.

            The arguments are lines to be drawn as lists of points.
            Points are a tuple, or other sequence:
            (r, θ) or (r, θ 'colour') or  (r, θ, 'colour', point_size)
            or (r, theta, 'colour', point_size, text)

            If the colour is not given the line is drawn in the
            default colour. The colour may be be any string that may be
            passed to QColor, such as a name like 'red' or
            a hex value such as '#F0F0F0'.

            The colour for the first point (if given) is used as the
            colour for the whole line. Any other colour parameters are
            ignored.

            Any point_size or text parameters with points are ignored.

            Any number of line arguments may be given, each drawn as a
            separate poly line.

            The draw method may be called multiple times. Each time old
            lines are removed and the new line argument(s) are drawn along
            with any text.

            Attribute `lines` contains the list of the lines passed as arguments.
            """

        # Save the arguments
        self.lines = args[:]

        # create the image as a pixmap
        self.graph_image = QPixmap(self.image_size_x, self.image_size_y)
        self.graph_image.fill(self.background)

        self._grid_and_texts()  # draw the grids and texts

        # draw on a pixmap using a painter
        painter = QPainter()
        painter.begin(self.graph_image)

        # draw the lines (if any):

        # draw lines using a QPainterPath to speed up rendering
        for line in args:
            # Create a QPainterPath
            path = QPainterPath()

            for i, point in enumerate(line):

                if i == 0:
                    # if a colour is passed, use it
                    if len(point) >= 3:  # if point has a colour field
                        painter.setPen(QColor(point[2]))
                    else:
                        painter.setPen(Qt.black)  # default colour

                    # first point is a move
                    path.moveTo(self.pr(point[0], point[1]), self.pt(point[0], point[1]))

                else:
                    # subsequent points

                    # draw the line
                    path.lineTo(self.pr(point[0], point[1]), self.pt(point[0], point[1]))

            painter.drawPath(path)

        painter.end()
        self.graph_label.setPixmap(self.graph_image)


def reCreateGraph(graph, new_x_size=None, new_y_size=None, new_text_pixel_size=None):
    """re-create the `graph` with the new sizes, if given.

        `graph` must be a Graph instance or descendant thereof.

        Returns the new instance of the graph"""

    if not isinstance(graph, Graph):
        raise NotAGraphError('The object passed to reCreateGraph is not a Graph or descendant thereof!')

    if new_x_size is None:
        new_x_size = graph.image_size_x

    if new_y_size is None:
        new_y_size = graph.image_size_y

    if new_text_pixel_size is None:
        new_text_pixel_size = graph.pixel_size

    graph_class = type(graph)

    new_graph = graph_class(graph.graph_label,
                            graph.xmin, graph.xmax,
                            graph.ymin, graph.ymax,
                            graph.xgrids, graph.ygrids,
                            new_x_size, new_y_size,
                            (graph.show_labels_x, graph.show_labels_y),
                            new_text_pixel_size,
                            graph.background)

    new_graph.set_grid_label_format(graph.xformat, graph.yformat)

    new_graph.texts = graph.texts[:]
    new_graph.polarTexts = graph.polarTexts[:]
    new_graph.centreMax = graph.centreMax

    # Call the draw method to show the grid, any texts and lines
    new_graph.draw(*graph.lines)

    return new_graph
