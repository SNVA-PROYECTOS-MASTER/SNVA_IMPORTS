# -*- coding: utf-8 -*-
{
    'name': 'SNVA Purchase Imports',
    'summary': 'Gestión integral de procesos de importación',
    'description': 'Este módulo permite gestionar de forma centralizada el proceso de importaciones, integrando información de órdenes de compra, facturas de proveedor, costos asociados (landed costs), y seguimiento logístico y contable. Facilita la trazabilidad, control de fechas clave y la correcta imputación contable de todos los elementos involucrados en una importación.',
    'license': 'LGPL-3',
    'author': 'Sinova',
    'website': 'https://www.sinova.co/',
    'version': '18.0.0.1',
    'category': 'summary',
    'depends': ['base', 'purchase', 'stock', 'account','documents','project'],
    
    'external_dependencies': {
    },
    
    'data': [
        'security/ir.model.access.csv',
        'security/purchase_import_security.xml',
        'data/purchase_import_sequence.xml',
        'data/purchase_order_sequence.xml',
        'views/purchase_import_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_import_line_views.xml',
        'wizards/purchase_import_wizard.xml',
    ],
    
    'application': True,
    'installable': True,
}
