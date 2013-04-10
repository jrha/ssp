#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2012  James Adams
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
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

from library import *

library = connect()

stats = library.query(sspStat).all()

hours = [s.hour for s in stats]
plays = [s.playcount for s in stats]
skips = [-s.skipcount for s in stats]

import matplotlib.pyplot as plt
plt.bar(hours, plays, color="#3465a4")
plt.bar(hours, skips, color="#f57900")
plt.xlim([0, 24])
plt.xticks(hours+[24])
plt.xlabel('Hour of day')
plt.ylabel('Skips vs Plays')
plt.show()
