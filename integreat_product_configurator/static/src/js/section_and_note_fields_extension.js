odoo.define('integreat_product_configurator.section_and_note_backend', function (require) {
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
        var dataPointId = record.id;
        if (record.context.configure_product && !record.data.product_id) {
            this.do_action('integreat_product_configurator.product_configurator_action', {
                additional_context: {
                    origin: 'order',
                    default_partner_id: record.context.default_partner_id || false,
                },
                on_close: function (res) {
                    if (res && res.return_default) { self.trigger_up('field_changed', {
                            dataPointID: dataPointId,
                            changes: res.return_default,
                        });
                    }
                },
            });
        }
        return $row;
    },

    _getRenderer: function () {
        return this._super.apply(this, arguments);
    },
});

return SectionAndNoteListRenderer;

});