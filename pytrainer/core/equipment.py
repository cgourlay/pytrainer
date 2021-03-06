# -*- coding: utf-8 -*-

#Copyright (C) Nathan Jones ncjones@users.sourceforge.net

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

import logging
from pytrainer.lib.ddbb import DeclarativeBase, ForcedInteger
from sqlalchemy import Column, Boolean, UnicodeText, Integer, Unicode
from sqlalchemy.orm import exc
from sqlalchemy.exc import IntegrityError
from pytrainer.core.activity import Activity
from sqlalchemy.sql import func

class Equipment(DeclarativeBase):
   """An equipment item that can be used during an activity, such as a pair of running shoes."""

   __tablename__ = 'equipment'
   active = Column(Boolean)
   description = Column(Unicode(length=100), unique=True, index=True)
   id = Column(Integer, primary_key=True)
   life_expectancy = Column(ForcedInteger)
   notes = Column(UnicodeText)
   prior_usage = Column(ForcedInteger)

   def __init__(self, **kwargs):
       self.description = u""
       self.active = True
       self.life_expectancy = 0
       self.prior_usage = 0
       self.notes = u""
       super(Equipment, self).__init__(**kwargs)

   def __eq__(self, o):
       if isinstance(o, Equipment):
           if self.id is not None and o.id is not None:
               return self.id == o.id
       return False
       
   def __hash__(self):
       if self.id is not None:
           return self.id
       else:
           return object.__hash__(self)

class EquipmentServiceException(Exception):
   
   def __init__(self, value):
       self.value = value
   
   def __str__(self):
       return repr(self.value)
       
class EquipmentService(object):
   
   """Provides access to stored equipment items."""
   
   def __init__(self, ddbb):
       self._ddbb = ddbb
       
   def get_all_equipment(self):
       """Get all equipment items."""
       return self._ddbb.session.query(Equipment).all()
   
   def get_active_equipment(self):
       """Get all the active equipment items."""
       return self._ddbb.session.query(Equipment).filter(Equipment.active == True).all()
   
   def get_equipment_item(self, item_id):
       """Get an individual equipment item by id.
       
       If no item with the given id exists then None is returned.
       """
       try:
           return self._ddbb.session.query(Equipment).filter(Equipment.id == item_id).one()
       except exc.NoResultFound:
           return None
       
   def store_equipment(self, equipment):
       """Store a new or update an existing equipment item.
       
       The stored object is returned."""
       logging.debug("Storing equipment item.")
       try:
          self._ddbb.session.add(equipment)
          self._ddbb.session.commit()
       except IntegrityError:
          raise EquipmentServiceException("An equipment item already exists with description '{0}'".format(equipment.description))
       return equipment

   def remove_equipment(self, equipment):
       """Remove an existing equipment item."""
       logging.debug("Deleting equipment item with id: '{0}'".format(equipment.id))
       self._ddbb.session.delete(equipment)
       self._ddbb.session.commit()
   
   def get_equipment_usage(self, equipment):
       """Get the total use of the given equipment."""
       result = self._ddbb.session.query(func.sum(Activity.distance).label('sum')).filter(Activity.equipment.contains(equipment))
       usage = result.scalar()
       return (0 if usage == None else float(usage)) + equipment.prior_usage
