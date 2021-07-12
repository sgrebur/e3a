odoo.define("web_dialog_size.web_action_history_back", function(require) {
    "use strict";

    var ActionManager = require('web.ActionManager');

    ActionManager.include({

        /**
         * Intersept action handling to detect extra action type
         * @override
         */
        _handleAction: function (action, options) {
            if (action.type === 'ir.actions.act_window_close' && action.effect === 'history_back') {
                return this.trigger_up("history_back");
            }
            return this._super.apply(this, arguments);
        },

    });
});
