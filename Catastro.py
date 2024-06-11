import os
from qgis.PyQt.QtCore import QCoreApplication, QSettings
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction, QInputDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsPointXY, QgsFields, QgsWkbTypes, Qgis, QgsMessageLog, QgsFillSymbol, QgsSingleSymbolRenderer
from PyQt5.QtCore import QVariant
import traceback

class Catastro:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr('Catastro')
        self.toolbar = self.iface.addToolBar(self.menu)
        self.toolbar.setObjectName(self.menu)

        self.settings = QSettings()

    def tr(self, message):
        return QCoreApplication.translate('Catastro', message)

    def initGui(self):
        icon_filtrar = os.path.join(self.plugin_dir, 'icon_filtrar.png')
        icon_quitar = os.path.join(self.plugin_dir, 'icon_quitar.png')
        icon_config = os.path.join(self.plugin_dir, 'icon_config.png')
        icon_trazar = os.path.join(self.plugin_dir, 'icon_trazar.png')
        
        self.add_action(
            icon_filtrar,
            text=self.tr('Filtrar Capa'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.add_action(
            icon_quitar,
            text=self.tr('Quitar Filtro'),
            callback=self.clear_filter,
            parent=self.iface.mainWindow())
        self.add_action(
            icon_config,
            text=self.tr('Configuración'),
            callback=self.show_config_dialog,
            parent=self.iface.mainWindow())
        self.add_action(
            icon_trazar,
            text=self.tr('Trazar'),
            callback=self.show_trazar_dialog,
            parent=self.iface.mainWindow())

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True, status_tip=None, whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr('&Catastro'), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        try:
            selected_layer = self.iface.activeLayer()
            if selected_layer:
                fields = selected_layer.fields()
                field_names = [field.name() for field in fields]

                attribute_name, ok = QInputDialog.getItem(self.iface.mainWindow(), "Seleccionar Atributo", "Selecciona un atributo para buscar:", field_names, 0, False)

                if ok and attribute_name:
                    clave, ok = QInputDialog.getText(self.iface.mainWindow(), "Ingresar Clave", "Ingresa la clave del polígono (completa, homoclave, manzana o nombre, separadas por comas):")

                    if ok and clave:
                        if clave.strip() == "":
                            QMessageBox.warning(self.iface.mainWindow(), "Advertencia", "La clave no puede estar vacía.")
                            return

                        claves = [c.strip() for c in clave.split(',') if c.strip()]
                        expressions = []

                        for c in claves:
                            if len(c) == 8:
                                expressions.append(f"lower(\"{attribute_name}\") = lower('{c}')")
                            elif len(c) == 2:
                                expressions.append(f"lower(substr(\"{attribute_name}\", 1, 2)) = lower('{c}')")
                            elif len(c) == 5:
                                expressions.append(f"(lower(substr(\"{attribute_name}\", 1, 2)) = lower('{c[:2]}') AND substr(\"{attribute_name}\", 3, 3) = '{c[2:]}')")
                            else:
                                expressions.append(f"lower(\"{attribute_name}\") LIKE lower('%{c}%')")

                        if expressions:
                            expression = " OR ".join(expressions)
                            selected_layer.setSubsetString(expression)
                            self.iface.mapCanvas().refresh()

                            if selected_layer.featureCount() == 0:
                                QMessageBox.warning(self.iface.mainWindow(), "Sin Resultados", "No se encontraron polígonos con esas claves.")
                                selected_layer.setSubsetString('')
                            else:
                                self.iface.zoomToActiveLayer()
                        else:
                            QMessageBox.critical(self.iface.mainWindow(), "Error", "No se ingresaron claves válidas.")
                    else:
                        QMessageBox.critical(self.iface.mainWindow(), "Error", "No se ingresó una clave válida.")
                else:
                    QMessageBox.critical(self.iface.mainWindow(), "Error", "No se seleccionó un atributo válido.")
            else:
                QMessageBox.critical(self.iface.mainWindow(), "Error", "No hay una capa activa seleccionada.")
        except Exception as e:
            error_message = str(e)
            QgsMessageLog.logMessage(f"Error: {error_message}\n{traceback.format_exc()}", 'Catastro', Qgis.Critical)
            QMessageBox.critical(self.iface.mainWindow(), "Error", f"Se ha producido un error: {error_message}")

    def clear_filter(self):
        try:
            layers = QgsProject.instance().mapLayers().values()
            for layer in layers:
                layer.setSubsetString('')
            self.iface.mapCanvas().refresh()
            QMessageBox.information(self.iface.mainWindow(), "Filtro Eliminado", "Se han eliminado todos los filtros.")
        except Exception as e:
            error_message = str(e)
            QgsMessageLog.logMessage(f"Error: {error_message}\n{traceback.format_exc()}", 'Catastro', Qgis.Critical)
            QMessageBox.critical(self.iface.mainWindow(), "Error", f"Se ha producido un error: {error_message}")

    def show_config_dialog(self):
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle('Configuración de Catastro')

        layout = QVBoxLayout()

        label = QLabel('Selecciona los atributos para el filtrado (separados por comas):')
        layout.addWidget(label)

        attribute_input = QLineEdit()
        attribute_input.setText(self.settings.value('catastro/attributes', 'cve_cat_or,clave,nom_fracci,nombre_com'))
        layout.addWidget(attribute_input)

        save_button = QPushButton('Guardar')
        save_button.clicked.connect(lambda: self.save_config(attribute_input.text(), dialog))
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def save_config(self, attributes, dialog):
        self.settings.setValue('catastro/attributes', attributes)
        dialog.accept()
        QMessageBox.information(self.iface.mainWindow(), 'Configuración Guardada', 'La configuración ha sido guardada.')

    def show_trazar_dialog(self):
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle('Trazar Polígono')
        layout = QVBoxLayout()

        self.table = QTableWidget(3, 2)
        self.table.setHorizontalHeaderLabels(['Y', 'X'])
        layout.addWidget(self.table)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Nombre del polígono (cve_cat_or)')
        layout.addWidget(self.name_input)

        add_row_button = QPushButton('Agregar Punto')
        add_row_button.clicked.connect(self.add_row)
        layout.addWidget(add_row_button)

        draw_button = QPushButton('Trazar')
        draw_button.clicked.connect(self.trazar_poligono)
        layout.addWidget(draw_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def add_row(self):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

    def trazar_poligono(self):
        points = []
        for row in range(self.table.rowCount()):
            y_item = self.table.item(row, 0)
            x_item = self.table.item(row, 1)
            if y_item and x_item:
                try:
                    y = float(y_item.text())
                    x = float(x_item.text())
                    points.append(QgsPointXY(x, y))
                except ValueError:
                    QMessageBox.warning(self.iface.mainWindow(), 'Error', 'Las coordenadas deben ser valores numéricos.')
                    return

        if len(points) < 3:
            QMessageBox.warning(self.iface.mainWindow(), 'Error', 'Se necesitan al menos 3 puntos para trazar un polígono.')
            return

        polygon = QgsGeometry.fromPolygonXY([points])
        layer = self.get_or_create_layer()

        feature = QgsFeature(layer.fields())
        feature.setGeometry(polygon)
        feature.setAttribute('cve_cat_or', self.name_input.text())

        layer.startEditing()
        layer.addFeature(feature)
        layer.commitChanges()
        self.iface.mapCanvas().refresh()

        # Aplicar simbología simple
        self.apply_simple_symbology(layer)

    def get_or_create_layer(self):
        layer_name = 'Polígonos Trazados'
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            return layers[0]

        fields = QgsFields()
        fields.append(QgsField('cve_cat_or', QVariant.String))
        layer = QgsVectorLayer('Polygon?crs=EPSG:32611', layer_name, 'memory')
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        QgsProject.instance().addMapLayer(layer)
        return layer

    def apply_simple_symbology(self, layer):
        symbol = QgsFillSymbol.createSimple({
            'color': '255,0,0,100',  # Color rojo con opacidad
            'outline_color': '0,0,0',  # Contorno negro
            'outline_width': '1'
        })
        renderer = QgsSingleSymbolRenderer(symbol)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
