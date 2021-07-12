odoo.define('integreat_sale_product_configurator.section_and_note_backend', function (require) {
"use strict";
var rpc = require('web.rpc');
var SectionAndNoteListRenderer = require('account.section_and_note_backend');

SectionAndNoteListRenderer.include({
    /**
     * We add the o_is_{display_type} class to allow custom behaviour both in JS and CSS.
     *
     * @override
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);

        if (record.data.display_type) {
            $row.addClass('o_is_' + record.data.display_type);
        }
        var self = this;
        var dataPointId = record.id
        if (record.context.configure_product && !record.data.product_id) {
            if (record.context.default_customer) {
                this.do_action('integreat_sale_product_configurator.sale_product_configurator_action', {
                    additional_context: {
                        tmpl_categ_id: record.context.tmpl_categ_id,
                        default_customer: record.context.default_customer,
                        default_pricelist_id: record.context.default_pricelist_id
                    },
                    on_close: function (res) {
                        if (res && res.return_default) { self.trigger_up('field_changed', {
                                dataPointID: dataPointId,
                                changes: res.return_default
                            });
                        }
                    }
                });
            } else {
                this.do_warn("Atención!", "¡Es obligatorio seleccionar al cliente!")
            }
        }
        return $row;
    },

    _getRenderer: function () {
        return this._super.apply(this, arguments);
    },
});

return SectionAndNoteListRenderer;

});