odoo.define('integreat_product_configurator.product_configurator_button', function (require) {
"use strict";

    var core = require('web.core');
    var ListView = require('web.ListView');
    var ListController = require('web.ListController');
    var KanbanView = require('web.KanbanView');
    var KanbanController = require('web.KanbanController')
    var FormView = require('web.FormView')
    var FormController = require('web.FormController')

    ListController.include({
        renderButtons: function($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                var custom_button = this.$buttons.find('button.oe_product_configurator_button');
                if (custom_button) {
                    custom_button.on('click', this.proxy('action_integreat_product_configurator'));
                }
            }
        },
        action_integreat_product_configurator: function() {
            this.do_action('integreat_product_configurator.product_configurator_action', {
                additional_context: {
                    default_origin: 'create',
                }
            });
        }
    });

    KanbanController.include({
        renderButtons: function($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                var custom_button = this.$buttons.find('button.oe_product_configurator_button');
                if (custom_button) {
                    custom_button.on('click', this.proxy('action_integreat_product_configurator'));
                }
            }
        },
        action_integreat_product_configurator: function() {
            this.do_action('integreat_product_configurator.product_configurator_action', {
                additional_context: {
                    default_origin: 'create',
                }
            });
        }
    });

    FormController.include({
        renderButtons: function($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                var custom_button = this.$buttons.find('button.oe_product_configurator_button');
                if (custom_button) {
                    custom_button.on('click', this.proxy('action_integreat_product_configurator'));
                }
            }
        },
        action_integreat_product_configurator: function() {
            this.do_action('integreat_product_configurator.product_configurator_action', {
                additional_context: {
                    default_origin: 'create',
                }
            });
        }
    });

});