from __future__ import division
from gettext import gettext as _

from base import ActorIcon, IconTexture

class ActorSourceIcon(ActorIcon):

    def __init__(self, stage, tooltip):
        super(ActorSourceIcon, self).__init__()

        self.texture = IconTexture(stage)
        self.texture.connect('button-press-event', self._on_button_press_cb)
        self.texture.connect('enter-event', self._enter_cb, tooltip)
        self.texture.connect('leave-event', self._leave_cb, tooltip)

    def set_icon(self, photoimage, x_offset, y_offset):
        super(ActorSourceIcon, self).set_icon(photoimage, x_offset, y_offset)

        if self.photo == None or self._check_hide_always():
            self.hide(True)
            return

        if photoimage.w > 80 and photoimage.h > 80: # for small photo image
            icon_pixbuf = self.icon_image.get_pixbuf()
            self.texture.change(icon_pixbuf, self.x, self.y)
            self.show()

    def show(self, force=False):
        mouse_on = self.photoimage.check_mouse_on_window()
        if (self.show_always or force or mouse_on) and self.photo and \
                not self._check_hide_always():
            self.texture.show()

    def _check_hide_always(self):
        info_obj = self.photo['info']()
        return hasattr(info_obj, 'hide_source_icon_on_image')

    def hide(self, force=False):
        mouse_on = self.photoimage.check_mouse_on_window() \
            if hasattr(self, 'photoimage') else False
        if (not self.show_always and not mouse_on) or force:
            self.texture.hide()

    def _get_icon(self):
        return self.photo.get('icon')()

    def _get_ui_data(self):
        self._set_ui_options('source', False, 1)

    def _on_button_press_cb(self, actor, event):
        self.photo.open()

    def _enter_cb(self, w, e, tooltip):
        tip = _("Open this photo")
        tooltip.update_text(tip)
