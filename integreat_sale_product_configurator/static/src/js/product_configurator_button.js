odoo.define('integreat_sale_product_configurator.IntegreatButtonFormController', function (require) {
"use strict";

var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var IntegreatButtonFormController = FormController.extend({
    /**
    * Override completely the default click behavior
    * otherwise for all buttons this dialog would be closed
    * moreover we don't need to perform any create/write action on the transient model
    * data changes on database models will be performed via _rpc @api.model passing all necessary args
    *
    * @override
    */
    _onButtonClicked: function (event) {
        var self = this;
        var attrs = event.data.attrs;
        if (attrs.name === 'add_to_sales_order_line') {
            this._onAddButtonClicked(event);
        } else if (attrs.name === 'create_attribute_value_1') {
            this._onAttrib1ButtonClicked(event);
        } else if (attrs.name === 'create_attribute_value_2') {
            this._onAttrib2ButtonClicked(event);
        } else if (attrs.name === 'create_attribute_value_3') {
            this._onAttrib3ButtonClicked(event);
        } else if (attrs.name === 'create_attribute_value_4') {
            this._onAttrib4ButtonClicked(event);
        } else if (attrs.name === 'create_product_variant') {
            this._onProductButtonClicked(event);
        }  else {
            this._onCancelButtonClicked(event);
        }
    },
    /**
    * Here the button actions from the wizard
    */
    _onAddButtonClicked: function (event) {
        var data = event.data.record.data;
        this.do_action({type: 'ir.actions.act_window_close', infos: {
                return_default: {
                    product_id: {id: data.product_id.res_id},
                    product_uom_qty: data.quantity,
                    price_unit: data.unit_price,
                }
            }
        });
    },
    /**
    * Here the button actions from the wizard
    */
    _onAttrib1ButtonClicked: function (event) {
        var self = this;
        var record = event.data.record;

        this._rpc({
            model: record.model,
            method: 'create_attribute_value',
            args: [
                record.data.tmpl_attribute_line_ids.data[4].res_id,
                record.data.pcattrnew1,
                record.data.pcattrid1.res_id
            ]
        }).then(function (attributeId) {
            self.trigger_up('field_changed', {
                    dataPointID: record.id,
                    changes: {button_handler: 1}
            })
        });
    },
    /**
    * Here the button actions from the wizard
    */
    _onAttrib2ButtonClicked: function (event) {
        var self = this;
        var record = event.data.record;
        this._rpc({
            model: record.model,
            method: 'create_attribute_value',
            args: [
                record.data.tmpl_attribute_line_ids.data[5].res_id,
                record.data.pcattrnew2,
                record.data.pcattrid2.res_id
            ]
        }).then( function(res) {
            self.trigger_up('field_changed', {
                    dataPointID: record.id,
                    changes: {button_handler: 2}
            })
        });
    },
    /**
    * Here the button actions from the wizard
    */
    _onAttrib3ButtonClicked: function (event) {
        var self = this;
        var record = event.data.record;

        this._rpc({
            model: record.model,
            method: 'create_attribute_value',
            args: [
                record.data.lamina_tmpl_attribute_line_ids.data[4].res_id,
                record.data.lattrnew1,
                record.data.lattrid1.res_id
            ]
        }).then(function (attributeId) {
            self.trigger_up('field_changed', {
                    dataPointID: record.id,
                    changes: {button_handler: 3}
            })
        });
    },
    /**
    * Here the button actions from the wizard
    */
    _onAttrib4ButtonClicked: function (event) {
        var self = this;
        var record = event.data.record;

        this._rpc({
            model: record.model,
            method: 'create_attribute_value',
            args: [
                record.data.lamina_tmpl_attribute_line_ids.data[5].res_id,
                record.data.lattrnew2,
                record.data.lattrid2.res_id
            ]
        }).then(function (attributeId) {
            self.trigger_up('field_changed', {
                    dataPointID: record.id,
                    changes: {button_handler: 4}
            })
        });
    },
    /**
    * Here the button actions from the wizard
    */
    _onProductButtonClicked: function (event) {
        var self = this;
        var data = event.data.record.data;
        var valueIds = JSON.stringify([data.pattr1.res_id, data.pattr2.res_id, data.pattr3.res_id, data.pattr4.res_id, data.pcattr1.res_id, data.pcattr2.res_id]);
        var values = {
            spec_calibre: data.pattr1.data.display_name,
            spec_papel: data.pattr2.data.display_name,
            spec_flauta: data.pattr3.data.display_name,
            spec_recub: data.pattr4.data.display_name,
            spec_ancho: data.pcattr1.data.display_name,
            spec_largo: data.pcattr2.data.display_name,
        };
        var productTemplateId = data.product_template_id.res_id;
        var params = {
            product_template_id: productTemplateId,
            product_template_attribute_value_ids: valueIds,
            values
        };
        if (data.create_lamina) {
            var valuesL = {
                isLamina = 
                spec_calibre: data.pattr1.data.display_name,
                spec_papel: data.pattr2.data.display_name,
                spec_flauta: data.pattr3.data.display_name,
                spec_recub: data.pattr4.data.display_name,
                spec_ancho: data.lattr1.data.display_name,
                spec_largo: data.lattr2.data.display_name,
                spec_marca1: data.marca1,
                spec_marca2: data.marca2,
                spec_marca3: data.marca3,
            };
            var valueIdsL = JSON.stringify([data.pattr1.res_id, data.pattr2.res_id, data.pattr3.res_id, data.pattr4.res_id, data.lattr1.res_id, data.lattr2.res_id]);
            var paramsL = {
                product_template_id: data.lamina_tmpl_id.res_id,
                product_template_attribute_value_ids: valueIdsL,
                valuesL
            };
            this._rpc({route: '/integreat_configurator/create_product_variant', params: paramsL}).then(function(laminaId) {
                self.trigger_up('field_changed', {
                    dataPointID: event.data.record.id,
                    changes: {lamina_id: {id: laminaId}},
                });
            });
        };
        this._rpc({route: '/integreat_configurator/create_product_variant', params: params}).then(function(productId) {
            self.trigger_up('field_changed', {
                dataPointID: event.data.record.id,
                changes: {product_id: {id: productId}},
            });
        });

    },
    /**
    * Button handler 3 will trigger update (write) methods
    *
    _onUpdateButtonClicked: function (event) {
        this.trigger_up('field_changed', {
                dataPointID: event.data.record.id,
                changes: {button_handler: 3},
        });
    },
    /
    /**
    * Here the button actions from the wizard
    */
    _onCancelButtonClicked: function (event) {
        var attrs = event.data.attrs;
        this.do_action({type: 'ir.actions.act_window_close', infos: {
                justSomeTestText: 'itt vagyunk!',
                justSomeOther: 'jo_helyen!'
            }
        });
    },
});

var IntegreatButtonFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: IntegreatButtonFormController,
    }),
});

viewRegistry.add('integreat_configurator_button', IntegreatButtonFormView);

});


