odoo.define('integreat_product_configurator.IntegreatButtonFormController', function (require) {
"use strict";

var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var IntegreatButtonFormController = FormController.extend({
    /**
    * @override
    **/
    _onButtonClicked: function (event) {
        this._super.apply(this, arguments);
        if (event.data.attrs.name === 'button_update_and_add') {
            var self = this;
            var record = event.data.record;
            function saveAndDelete () {
                return self.saveRecord(self.handle, {
                    stayInEdit: false,
                });
                then(function () {
                    // we need to reget the record to make sure we have changes made
                    // by the basic model, such as the new res_id, if the record is new.
                    var savedId = self.model.get(event.data.record.id.res_id);
                    return self._rpc({model: record.model, method: 'unlink', args: [savedId]});
                });
            }
            saveAndDelete().then(function () {
                return self.do_action({
                    type: 'ir.actions.act_window_close',
                    infos: {return_default: {product_id: {id: record.data.product_id.res_id}}}
                });
            });
        }
    },
});

var IntegreatButtonFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: IntegreatButtonFormController,
    }),
});

viewRegistry.add('integreat_configurator_button', IntegreatButtonFormView);

});


