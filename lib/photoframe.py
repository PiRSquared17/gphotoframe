import os
import time
import sys
from xml.sax.saxutils import escape
from urlparse import urlparse

import gobject
import gtk
import gtk.glade
from twisted.internet import reactor

import constants
from preferences import Preferences
from utils.config import GConf

class PhotoFrame(object):
    """Photo Frame Window"""

    def __init__(self, photolist):

        self.photolist = photolist
        gui = gtk.glade.XML(constants.GLADE_FILE)

        self.conf = GConf()
        self.conf.set_notify_add('window_sticky', self._change_sticky_cb)
        self.conf.set_notify_add('window_fix', self._change_window_fix_cb)

        self.window = gui.get_widget('window')
        self.window.set_decorated(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_gravity(gtk.gdk.GRAVITY_CENTER)
        if self.conf.get_bool('window_sticky'):
            self.window.stick()
        self._set_window_state(gui)
        self._set_window_position()

        self.photoimage = PhotoImage(gui, self)
        self.popup_menu = PopUpMenu(self.photolist, self)
        self._set_accelerator()

        dic = { 
            "on_window_button_press_event" : self._check_button_cb,
            "on_window_leave_notify_event" : self._save_geometry_cb,
            "on_window_window_state_event" : self._window_state_cb,
            # "on_window_destroy" : reactor.stop,
            }
        gui.signal_autoconnect(dic)

    def set_photo(self, photo):
        self.photoimage.set_photo(photo)

        if hasattr(self, "fullframe") and self.fullframe.window.window:
            self.fullframe.set_photo(photo)

    def set_no_photo(self):
        self.photoimage.set_no_photo()

    def _set_window_position(self):
        self.window.move(self.conf.get_int('root_x'), 
                         self.conf.get_int('root_y'))
        self.window.resize(1, 1)
        self.window.show_all()
        self.window.get_position()

    def _set_window_state(self, gui):
        if self.conf.get_bool('window_fix'):
            self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        self.window.set_keep_below(True)

    def _toggle_fullscreen(self):
        self.fullframe = PhotoFrameFullScreen(self.photolist)
        photo = self.photoimage.photo
        self.fullframe.set_photo(photo)

    def _set_accelerator(self):
        accel_group = gtk.AccelGroup()
        ac_set = [[ "<gph>/quit", "<control>q", self.popup_menu.quit ],
                  [ "<gph>/open", "<control>o", self.popup_menu.open_photo ]]
        for ac in ac_set:
            key, mod = gtk.accelerator_parse(ac[1])
            gtk.accel_map_add_entry(ac[0], key, mod)
            accel_group.connect_by_path(ac[0], ac[2])

        self.window.add_accel_group(accel_group) 

    def _check_button_cb(self, widget, event):
        if event.button == 1:
            widget.begin_move_drag(
                event.button, int(event.x_root), int(event.y_root), event.time)
        elif event.button == 2:
            self._toggle_fullscreen()
        elif event.button == 3:
            self.popup_menu.start(widget, event)
        elif event.button == 9:
            self.photolist.next_photo()

    def _window_state_cb(self, widget, event):
        if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
            state = event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED
            self.window.set_skip_taskbar_hint(not state)

    def _save_geometry_cb(self, widget, event):
        if event.mode != 2:
            return True

        x, y = widget.get_position()
        w, h = widget.get_size()
        self.conf.set_int( 'root_x', x + w / 2)
        self.conf.set_int( 'root_y', y + h / 2)
        return False

    def _change_window_fix_cb(self, client, id, entry, data):
        hint = gtk.gdk.WINDOW_TYPE_HINT_DOCK \
            if entry.value.get_bool() else gtk.gdk.WINDOW_TYPE_HINT_NORMAL

        self.window.hide()
        self.window.set_type_hint(hint)
        self.photoimage.clear()

        self._set_window_position()
        time.sleep(0.5)
        self.photoimage.set_photo()

    def _change_sticky_cb(self, client, id, entry, data):
        if entry.value.get_bool():
            self.window.stick()
        else:
            self.window.unstick()

class PhotoFrameFullScreen(PhotoFrame):
    def set_photo(self, photo):
        self.photoimage.set_photo(photo)

    def _set_window_state(self, gui):
        for widget in [gui.get_widget('eventbox'), gui.get_widget('window')]:
            widget.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        self.window.fullscreen()

    def _toggle_fullscreen(self):
        self.window.destroy()

    def _save_geometry_cb(self, widget, event):
        pass

    def _change_window_fix_cb(self, client, id, entry, data):
        pass

class PhotoImage(object):
    def __init__(self, gui, photoframe):
        self.image = gui.get_widget('image')
        self.window = gui.get_widget('window')
        self.conf = GConf()
        self.photoframe = photoframe

    def set_photo(self, photo=None):
        if photo:
            self.photo = photo

        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(self.photo['filename'])
        except gobject.GError:
            print sys.exc_info()[1]
            return
        else:
            pixbuf = self._rotate(pixbuf)
            pixbuf = self._scale(pixbuf)

            self._set_image(pixbuf)
            self._set_tips()

    def set_no_photo(self):
        pixbuf = self._no_image()
        self.photo = None
        self._set_image(pixbuf)
        self.window.set_tooltip_markup(None)

    def clear(self):
        self.image.clear()

    def is_accessible_local_file(self):
        if self.photo is None:
            return False

        url = urlparse(self.photo['url'])
        if url.scheme == 'file' and not os.path.exists(self.photo['filename']):
            return False
        else:
            return True

    def _set_image(self, pixbuf):
        self.image.set_from_pixbuf(pixbuf)

        w = pixbuf.get_width()
        h = pixbuf.get_height()
        border = self.conf.get_int('border_width', 10)
        self.window.resize(w + border, h + border)

    def _set_tips(self):
        title = self.photo.get('title')
        owner = self.photo.get('owner_name')
        title = "<big>%s</big>" % escape(title) if title else ""
        owner = "by " + escape(owner) if owner else ""
        if title and owner:
            title += "\n"

        try:
            self.window.set_tooltip_markup(title + owner)
        except:
            pass

    def _rotate(self, pixbuf):
        orientation = pixbuf.get_option('orientation') or 1

        if orientation == '6':
            rotate = 270
        elif orientation == '8':
            rotate = 90
        else:
            rotate = 0

        pixbuf = pixbuf.rotate_simple(rotate)
        return pixbuf

    def _scale(self, pixbuf):
        max_w = float( self.conf.get_int('max_width', 400) )
        max_h = float( self.conf.get_int('max_height', 300) )

        if isinstance(self.photoframe, PhotoFrameFullScreen):
            screen = gtk.gdk.screen_get_default()
            display_num = screen.get_monitor_at_window(self.window.window)
            geometry = screen.get_monitor_geometry(display_num)
            max_w = float(geometry.width)
            max_h = float(geometry.height)

        src_w = pixbuf.get_width() 
        src_h = pixbuf.get_height()

        if src_w / max_w > src_h / max_h:
            ratio = max_w / src_w
        else:
            ratio = max_h / src_h

        w = int( src_w * ratio + 0.4 )
        h = int( src_h * ratio + 0.4 )

        pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
        return pixbuf

    def _no_image(self):
        gdk_window = self.window.window
        w = self.conf.get_int('max_width', 400)
        h = self.conf.get_int('max_height', 300)

        pixmap = gtk.gdk.Pixmap(gdk_window, w, h, -1)
        colormap = gtk.gdk.colormap_get_system()
        gc = gtk.gdk.Drawable.new_gc(pixmap)
        gc.set_foreground(colormap.alloc_color(0, 0, 0))
        pixmap.draw_rectangle(gc, True, 0, 0, w, h)

        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, w, h)
        pixbuf.get_from_drawable(pixmap, colormap, 0, 0, 0, 0, w, h)

        return pixbuf

class PopUpMenu(object):
    def __init__(self, photolist, photoframe):
        self.gui = gtk.glade.XML(constants.GLADE_FILE)
        self.photoimage = photoframe.photoimage
        self.conf = GConf()

        preferences = Preferences(photolist)
        about = AboutDialog()

        dic = { 
            "on_menuitem5_activate" : self.open_photo,
            "on_menuitem6_toggled"  : self._fix_window_cb,
            "on_prefs" : preferences.start,
            "on_about" : about.start,
            "on_quit"  : self.quit,
            }
        self.gui.signal_autoconnect(dic)

        if self.conf.get_bool('window_fix'):
            self.gui.get_widget('menuitem6').set_active(True)

    def start(self, widget, event):
        state = self.photoimage.is_accessible_local_file()
        self.gui.get_widget('menuitem5').set_sensitive(state)
        menu = self.gui.get_widget('menu')
        menu.popup(None, None, None, event.button, event.time)

    def quit(self, *args):
        reactor.stop()

    def open_photo(self, *args):
        self.photoimage.photo.open()

    def _fix_window_cb(self, widget):
        self.conf.set_bool('window_fix', widget.get_active())

class AboutDialog(object):
    def start(self, *args):
        gui = gtk.glade.XML(constants.GLADE_FILE)
        about = gui.get_widget('aboutdialog')
        about.set_property('version', constants.VERSION)
        gtk.about_dialog_set_url_hook(self._open_url)
        about.run()
        about.destroy()

    def _open_url(self, about, url):
        os.system("gnome-open '%s'" % url)
