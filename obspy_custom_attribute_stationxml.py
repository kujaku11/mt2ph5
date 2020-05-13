# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 19:26:01 2019

@author: jpeacock
"""

from obspy.core import inventory
from obspy.core.util import AttribDict

ns = 'MT'
code = 'MT666'

station_01 = inventory.Station(code, 40.0, -115.0, 1000)
channel_01 = inventory.Channel('SQE', "", 39.0, -112.0, 150, 0, azimuth=90,
                               sample_rate=256, dip=0, 
                               types=['ELECTRIC POTENTIAL'])

channel_01.start_date = '2020-01-01T12:20:05.000000Z'
channel_01.end_date = '2020-01-05T62:40:15.000000Z'


channel_01.comments.append(inventory.Comment("DipoleLength = 10 meters"))
channel_01.extra = AttribDict()
channel_01.extra.DipoleLength = AttribDict()
channel_01.extra.DipoleLength.value = '10'
channel_01.extra.DipoleLength.namespace = ns
channel_01.extra.DipoleLength.attrib = {'units':'meters'}

channel_01.extra.FieldNotes = AttribDict({'namespace':ns})
channel_01.extra.FieldNotes.value = AttribDict()

channel_01.extra.FieldNotes.value.ContactResistanceA = AttribDict()
channel_01.extra.FieldNotes.value.ContactResistanceA.value = 1.2
channel_01.extra.FieldNotes.value.ContactResistanceA.namespace = ns
channel_01.extra.FieldNotes.value.ContactResistanceA.attrib = {'units': 'kOhms'}

channel_01.extra.FieldNotes.value.ContactResistanceB = AttribDict()
channel_01.extra.FieldNotes.value.ContactResistanceB.value = 1.8
channel_01.extra.FieldNotes.value.ContactResistanceB.namespace = ns
channel_01.extra.FieldNotes.value.ContactResistanceB.attrib = {'units': 'kOhms'}

# notes
station_01.channels.append(channel_01)

n = inventory.Network('MT666')
n.stations = [station_01]

inv = inventory.Inventory([n], code)
inv.write('my_inventory.xml', format='STATIONXML')