# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2012 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
The window displayed when a Document is modified by an external program.
"""

from __future__ import unicode_literals

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import app
import qutil
import util
import icons
import htmldiff
import document
import widgets.dialog
import documentwatcher
import help.html

from . import enabled, setEnabled


def window():
    global _window
    try:
        return _window
    except NameError:
        _window = ChangedDocumentsListDialog()
    return _window


class ChangedDocumentsListDialog(widgets.dialog.Dialog):
    def __init__(self):
        super(ChangedDocumentsListDialog, self).__init__(buttons=('close',))
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        
        layout = QGridLayout(margin=0)
        self.mainWidget().setLayout(layout)
        self.tree = QTreeWidget(headerHidden=True, rootIsDecorated=False,
                                columnCount=2, itemsExpandable=False)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        
        self.buttonReload = QPushButton()
        self.buttonReloadAll = QPushButton()
        self.buttonSave = QPushButton()
        self.buttonSaveAll = QPushButton()
        self.buttonShowDiff = QPushButton()
        self.checkWatchingEnabled = QCheckBox(checked=enabled())
        
        layout.addWidget(self.tree, 0, 0, 6, 1)
        layout.addWidget(self.buttonReload, 0, 1)
        layout.addWidget(self.buttonReloadAll, 1, 1)
        layout.addWidget(self.buttonSave, 2, 1)
        layout.addWidget(self.buttonSaveAll, 3, 1)
        layout.addWidget(self.buttonShowDiff, 4, 1)
        layout.addWidget(self.checkWatchingEnabled, 6, 0, 1, 2)
        layout.setRowStretch(5, 10)
        
        app.documentClosed.connect(self.removeDocument)
        app.documentSaved.connect(self.removeDocument)
        app.documentUrlChanged.connect(self.removeDocument)
        app.documentLoaded.connect(self.removeDocument)
        self.tree.itemSelectionChanged.connect(self.updateButtons)
        self.buttonReload.clicked.connect(self.slotButtonReload)
        self.buttonReloadAll.clicked.connect(self.slotButtonReloadAll)
        self.buttonSave.clicked.connect(self.slotButtonSave)
        self.buttonSaveAll.clicked.connect(self.slotButtonSaveAll)
        self.buttonShowDiff.clicked.connect(self.slotButtonShowDiff)
        self.checkWatchingEnabled.toggled.connect(setEnabled)
    
        app.translateUI(self)
        qutil.saveDialogSize(self, 'externalchanges/dialog/size', QSize(400, 200))
        help.addButton(self.buttonBox(), "help_external_changes")
        self.button('close').setFocus()
    
    def translateUI(self):
        self.setWindowTitle(app.caption(_("Modified Files")))
        self.setMessage(_(
            "The following files were modified or deleted by other "
            "applications:"))
        self.buttonReload.setText(_("Reload"))
        self.buttonReload.setToolTip(_(
            "Reloads the selected documents from disk. "
            "(You can still reach the previous state of the document "
            "using the Undo command.)"))
        self.buttonReloadAll.setText(_("Reload All"))
        self.buttonReloadAll.setToolTip(_(
            "Reloads all externally modified documents from disk. "
            "(You can still reach the previous state of the document "
            "using the Undo command.)"))
        self.buttonSave.setText(_("Save"))
        self.buttonSave.setToolTip(_(
            "Saves the selected documents to disk, overwriting the "
            "modifications by another program."))
        self.buttonSaveAll.setText(_("Save All"))
        self.buttonSaveAll.setToolTip(_(
            "Saves all documents to disk, overwriting the modifications by "
            "another program."))
        self.buttonShowDiff.setText(_("Show Difference..."))
        self.buttonShowDiff.setToolTip(_(
            "Shows the differences between the current document "
            "and the file on disk."))
        self.checkWatchingEnabled.setText(_(
            "Enable watching documents for external changes"))
        self.checkWatchingEnabled.setToolTip(_(
            "If checked, Frescobaldi will warn you when opened files are "
            "modified or deleted by other applications."))
    
    def setDocuments(self, documents):
        """Display the specified documents in the list."""
        # clear the treewidget
        for d in self.tree.invisibleRootItem().takeChildren():
            for i in d.takeChildren():
                i.doc = None
        # group the documents by directory
        dirs = {}
        for d in documents:
            path = d.url().toLocalFile()
            if path:
                dirname, filename = os.path.split(path)
                dirs.setdefault(dirname, []).append((filename, d))
        for dirname in sorted(dirs, key=util.naturalsort):
            diritem = QTreeWidgetItem()
            diritem.setText(0, util.homify(dirname))
            self.tree.addTopLevelItem(diritem)
            diritem.setExpanded(True)
            diritem.setFlags(Qt.ItemIsEnabled)
            diritem.setIcon(0, icons.get('folder-open'))
            for filename, document in sorted(dirs[dirname],
                                              key=lambda item: util.naturalsort(item[0])):
                fileitem = QTreeWidgetItem()
                diritem.addChild(fileitem)
                if documentwatcher.DocumentWatcher.instance(document).isdeleted():
                    itemtext = _("[deleted]") 
                    icon = "dialog-error"
                else:
                    itemtext = _("[modified]")
                    icon = "document-edit"
                fileitem.setIcon(0, icons.get(icon))
                fileitem.setText(0, filename)
                fileitem.setText(1, itemtext)
                fileitem.doc = document
        # select the item if there is only one
        if len(dirs) == 1 and len(dirs.values()[0]) == 1:
            fileitem.setSelected(True)
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        self.updateButtons()
        
    def removeDocument(self, document):
        """Remove the specified document from our list."""
        for d in range(self.tree.topLevelItemCount()):
            diritem = self.tree.topLevelItem(d)
            for f in range(diritem.childCount()):
                if diritem.child(f).doc is document:
                    i = diritem.takeChild(f)
                    i.doc = None
                    if diritem.childCount() == 0:
                        self.tree.takeTopLevelItem(d)
                    break
            else:
                continue
            break
        self.updateButtons()
        # hide if no documents are left
        if self.tree.topLevelItemCount() == 0:
            self.hide()
    
    def selectedDocuments(self):
        """Return the selected documents."""
        return [i.doc for i in self.tree.selectedItems()]
    
    def allDocuments(self):
        """Return all shown documents."""
        return [self.tree.topLevelItem(d).child(f).doc
                for d in range(self.tree.topLevelItemCount())
                for f in range(self.tree.topLevelItem(d).childCount())]
    
    def updateButtons(self):
        """Updates the buttons regarding the selection."""
        docs_sel = self.selectedDocuments()
        docs_all = self.allDocuments()
        all_deleted_sel = all(documentwatcher.DocumentWatcher.instance(d).isdeleted()
                              for d in docs_sel)
        all_deleted_all = all(documentwatcher.DocumentWatcher.instance(d).isdeleted()
                              for d in docs_all)
        self.buttonSave.setEnabled(len(docs_sel) > 0)
        self.buttonSaveAll.setEnabled(len(docs_all) > 0)
        self.buttonReload.setEnabled(not all_deleted_sel)
        self.buttonReloadAll.setEnabled(not all_deleted_all)
        self.buttonShowDiff.setEnabled(len(docs_sel) == 1 and not all_deleted_sel)
    
    def slotButtonReload(self):
        """Called when the user clicks Reload."""
        for d in self.selectedDocuments():
            d.load(True)
        
    def slotButtonReloadAll(self):
        """Called when the user clicks Reload All."""
        for d in self.allDocuments():
            d.load(True)
    
    def slotButtonSave(self):
        """Called when the user clicks Save."""
        self.saveDocuments(self.selectedDocuments())
    
    def slotButtonSaveAll(self):
        """Called when the user clicks Save All."""
        self.saveDocuments(self.allDocuments())
    
    def saveDocuments(self, documents):
        """Used by slotButtonSave and slotButtonSaveAll."""
        results = [d.save() for d in documents]
        if False in results:
            if len(documents) == 1:
                msg = _("The document could not be saved.")
            elif results.count(False) == 1:
                msg = _("One document could not be saved.")
            else:
                msg = _("Some documents could not be saved.")
            QMessageBox.warning(self, app.caption(_("Error")), "\n".join((msg,
            _("Maybe the directory does not exist anymore."),
            _("Please save the document using the \"Save As...\" dialog.",
              "Please save the documents using the \"Save As...\" dialog.",
              results.count(False)))))
        
    def slotButtonShowDiff(self):
        """Called when the user clicks Show Difference."""
        docs = self.selectedDocuments() or self.allDocuments()
        if not docs:
            return
        d = docs[0]
        if documentwatcher.DocumentWatcher.instance(d).isdeleted():
            return
        
        filename = d.url().toLocalFile()
        try:
            with open(filename) as f:
                disktext = util.decode(f.read())
        except (IOError, OSError):
            return
        
        currenttext = d.toPlainText()
        
        html = htmldiff.htmldiff(
            currenttext, disktext, 
            _("Current Document"), _("Document on Disk"), numlines=5)
        dlg = widgets.dialog.Dialog(self, buttons=('close',))
        view = QTextBrowser(lineWrapMode=QTextBrowser.NoWrap)
        view.setHtml(html)
        dlg.setMainWidget(view)
        dlg.setWindowTitle(app.caption("Differences"))
        dlg.setMessage(_(
            "Document: {url}\n"
            "Difference between the current document and the file on disk:").format(
                url=filename))
        dlg.setWindowModality(Qt.NonModal)
        dlg.setAttribute(Qt.WA_QuitOnClose, False)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        qutil.saveDialogSize(dlg, "externalchanges/diff/dialog/size", QSize(600, 300))
        dlg.show()


class help_external_changes(help.page):
    def title():
        return _("Modified Files")
    
    def body():
        return help.html.p(
        _("Frescobaldi can detect if files are modified or deleted by other "
          "applications."),
        _("When another application modifies or deletes one or more documents "
          "that are opened in Frescobaldi, a list of affected documents is "
          "displayed, and you can choose whether to reload one or more "
          "documents from disk, or to save them, discarding the modifications "
          "made by the other application."),
        _("When a document is reloaded, you can still press {undokey} to get "
          "back the document as it was in memory before reloading it from disk."
           ).format(undokey=help.shortcut(help.action("main", "edit_undo"))),
        _("Press the <em>{showdiff}</em> button to see the difference between the "
          "current document and its version on disk.").format(
            showdiff=_("Show Difference...")),
        _("If you don't want to be warned when a document is changed or deleted "
          "by another application, uncheck the <em>{action}</em> checkbox."
          ).format(action=_("Enable watching documents for external changes")))


