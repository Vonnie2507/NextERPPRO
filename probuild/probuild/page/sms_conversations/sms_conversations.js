frappe.pages['sms-conversations'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'SMS Conversations',
        single_column: true
    });

    page.add_action_icon("refresh", function() {
        page.sms_conversations.refresh();
    });

    page.add_action_icon("arrow-left", function() {
        window.history.back();
    });

    // Wait for page to be ready
    $(wrapper).on('show', function() {
        if (!page.sms_conversations) {
            page.sms_conversations = new SMSConversations(page, wrapper);
        } else {
            page.sms_conversations.refresh();
        }
    });

    // Also initialize immediately
    page.sms_conversations = new SMSConversations(page, wrapper);
};

class SMSConversations {
    constructor(page, wrapper) {
        this.page = page;
        this.wrapper = wrapper;
        this.$container = $(wrapper).find('.layout-main-section');
        this.current_conversation = null;
        this.setup_layout();
        this.load_conversations();
    }

    setup_layout() {
        this.$container.html(`
            <style>
                .sms-container { display: flex; height: calc(100vh - 150px); }
                .conversations-list { width: 350px; border-right: 1px solid #d1d8dd; overflow-y: auto; background: #fff; }
                .conversation-item { padding: 12px 15px; border-bottom: 1px solid #eee; cursor: pointer; }
                .conversation-item:hover { background: #f5f7fa; }
                .conversation-item.active { background: #e8f0fe; }
                .unread-badge { background: #e74c3c; color: white; border-radius: 10px; padding: 2px 8px; font-size: 11px; }
                .chat-container { flex: 1; display: flex; flex-direction: column; background: #fff; }
                .chat-header { padding: 15px; border-bottom: 1px solid #d1d8dd; background: #f5f7fa; display: flex; justify-content: space-between; align-items: center; }
                .chat-messages { flex: 1; overflow-y: auto; padding: 20px; background: #fafbfc; }
                .message-bubble { max-width: 70%; margin: 8px 0; padding: 10px 14px; border-radius: 18px; }
                .message-bubble.outbound { background: #0084ff; color: white; margin-left: auto; border-bottom-right-radius: 4px; }
                .message-bubble.inbound { background: #e4e6eb; color: #000; border-bottom-left-radius: 4px; }
                .message-time { font-size: 11px; opacity: 0.7; margin-top: 4px; }
                .message-sender { font-size: 11px; opacity: 0.8; margin-bottom: 4px; font-weight: 500; }
                .chat-input { padding: 15px; border-top: 1px solid #d1d8dd; display: flex; gap: 10px; }
                .chat-input textarea { flex: 1; border-radius: 20px; padding: 10px 15px; border: 1px solid #d1d8dd; resize: none; }
                .chat-input button { border-radius: 20px; padding: 10px 20px; }
                .date-separator { text-align: center; margin: 20px 0; color: #8d99a6; font-size: 12px; }
                .empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: #8d99a6; }
            </style>
            <div class="sms-container">
                <div class="conversations-list"></div>
                <div class="chat-container">
                    <div class="empty-state">Select a conversation to view messages</div>
                </div>
            </div>
        `);
    }

    load_conversations() {
        frappe.call({
            method: 'probuild.probuild.api.twilio.get_conversations',
            callback: (r) => {
                if (r.message) {
                    this.render_conversations(r.message);
                }
            }
        });
    }

    render_conversations(conversations) {
        const $list = this.$container.find('.conversations-list');
        $list.empty();

        if (conversations.length === 0) {
            $list.html('<div class="p-3 text-muted">No SMS conversations yet</div>');
            return;
        }

        conversations.forEach(conv => {
            const name = conv.contact_name || conv.phone_number;
            const time = frappe.datetime.prettyDate(conv.last_message_time);
            const preview = conv.last_message.substring(0, 40) + (conv.last_message.length > 40 ? '...' : '');
            const unread = conv.unread_count > 0 ? `<span class="unread-badge">${conv.unread_count}</span>` : '';
            const direction = conv.direction === 'Inbound' ? '←' : '→';

            $list.append(`
                <div class="conversation-item" data-phone="${conv.phone_number}">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>${frappe.utils.escape_html(name)}</strong>
                        ${unread}
                    </div>
                    <div class="text-muted small mt-1">${direction} ${frappe.utils.escape_html(preview)}</div>
                    <div class="text-muted small">${time}</div>
                </div>
            `);
        });

        $list.find('.conversation-item').click((e) => {
            const phone = $(e.currentTarget).data('phone');
            const conv = conversations.find(c => c.phone_number === phone);
            this.load_conversation(conv);
            $list.find('.conversation-item').removeClass('active');
            $(e.currentTarget).addClass('active');
        });
    }

    load_conversation(conv) {
        this.current_conversation = conv;

        frappe.call({
            method: 'probuild.probuild.api.twilio.get_conversation_messages',
            args: { phone_number: conv.phone_number },
            callback: (r) => {
                if (r.message) {
                    this.render_chat(conv, r.message);
                    
                    if (conv.unread_count > 0) {
                        this.mark_conversation_read(conv.phone_number);
                    }
                }
            }
        });
    }

    render_chat(conv, messages) {
        const name = conv.contact_name || conv.phone_number;
        const $chatContainer = this.$container.find('.chat-container');

        $chatContainer.html(`
            <div class="chat-header">
                <div>
                    <strong>${frappe.utils.escape_html(name)}</strong>
                    <div class="text-muted small">${conv.phone_number}</div>
                </div>
                <div>
                    <button class="btn btn-sm btn-default mark-read-btn" ${conv.unread_count > 0 ? '' : 'style="display:none"'}>✓ Mark Read</button>
                    <button class="btn btn-sm btn-default mark-unread-btn" ${conv.unread_count === 0 ? '' : 'style="display:none"'}>↩ Mark Unread</button>
                    <button class="btn btn-sm btn-default attach-btn">📎 Attach</button>
                </div>
            </div>
            <div class="chat-messages"></div>
            <div class="chat-input">
                <textarea placeholder="Type a message..." rows="2"></textarea>
                <button class="btn btn-primary send-btn">Send</button>
            </div>
        `);

        this.render_messages(messages);

        $chatContainer.find('.send-btn').click(() => this.send_message(conv.phone_number));
        $chatContainer.find('textarea').keydown((e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send_message(conv.phone_number);
            }
        });
        $chatContainer.find('.mark-read-btn').click(() => this.mark_conversation_read(conv.phone_number));
        $chatContainer.find('.mark-unread-btn').click(() => this.mark_conversation_unread(conv.phone_number));
        $chatContainer.find('.attach-btn').click(() => this.show_attach_dialog(conv.phone_number));
    }

    render_messages(messages) {
        const $msgContainer = this.$container.find('.chat-messages');
        $msgContainer.empty();

        let lastDate = null;

        messages.forEach(msg => {
            const msgDate = frappe.datetime.str_to_obj(msg.sent_at).toDateString();

            if (msgDate !== lastDate) {
                const dateLabel = frappe.datetime.prettyDate(msg.sent_at);
                $msgContainer.append(`<div class="date-separator"><span>${dateLabel}</span></div>`);
                lastDate = msgDate;
            }

            const time = frappe.datetime.str_to_obj(msg.sent_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            const statusIcon = msg.status === 'Sent' ? '✓' : (msg.status === 'Failed' ? '✗' : '');
            const senderName = msg.direction === 'Outbound' && msg.sender_full_name ? `<div class="message-sender">${msg.sender_full_name}</div>` : '';

            $msgContainer.append(`
                <div class="message-bubble ${msg.direction.toLowerCase()}">
                    ${senderName}
                    <div class="message-text">${frappe.utils.escape_html(msg.message)}</div>
                    <div class="message-time">
                        ${time}
                        ${msg.direction === 'Outbound' ? `<span class="message-status">${statusIcon}</span>` : ''}
                    </div>
                </div>
            `);
        });

        $msgContainer.scrollTop($msgContainer.prop("scrollHeight"));
    }

    send_message(phone_number) {
        const $textarea = this.$container.find('.chat-input textarea');
        const message = $textarea.val().trim();

        if (!message) return;

        const $btn = this.$container.find('.send-btn');
        $btn.prop('disabled', true).text('Sending...');

        frappe.call({
            method: 'probuild.probuild.api.twilio.send_sms',
            args: {
                recipient_number: phone_number,
                message: message,
                linked_doctype: this.current_conversation?.linked_doctype,
                linked_name: this.current_conversation?.linked_name,
                contact_name: this.current_conversation?.contact_name
            },
            callback: (r) => {
                $btn.prop('disabled', false).text('Send');
                if (r.message && r.message.success) {
                    $textarea.val('');
                    this.load_conversation(this.current_conversation);
                    frappe.show_alert({ message: 'SMS sent!', indicator: 'green' });
                } else {
                    frappe.msgprint({ title: 'Error', message: r.message?.error || 'Failed to send', indicator: 'red' });
                }
            },
            error: () => {
                $btn.prop('disabled', false).text('Send');
            }
        });
    }

    mark_conversation_read(phone_number) {
        frappe.call({
            method: 'probuild.probuild.api.twilio.mark_conversation_read',
            args: { phone_number: phone_number },
            callback: (r) => {
                if (r.message?.success) {
                    this.load_conversations();
                    if (this.current_conversation) {
                        this.current_conversation.unread_count = 0;
                        this.$container.find('.mark-read-btn').hide();
                        this.$container.find('.mark-unread-btn').show();
                    }
                }
            }
        });
    }

    mark_conversation_unread(phone_number) {
        frappe.call({
            method: 'probuild.probuild.api.twilio.mark_conversation_unread',
            args: { phone_number: phone_number },
            callback: (r) => {
                if (r.message?.success) {
                    this.load_conversations();
                    if (this.current_conversation) {
                        this.current_conversation.unread_count = r.message.new_unread_count;
                        this.$container.find('.mark-unread-btn').hide();
                        this.$container.find('.mark-read-btn').show();
                    }
                }
            }
        });
    }

    show_attach_dialog(phone_number) {
        let d = new frappe.ui.Dialog({
            title: 'Attach Conversation',
            fields: [
                { fieldname: 'doctype', fieldtype: 'Select', label: 'Attach To', options: 'Opportunity\nProject', reqd: 1 },
                { fieldname: 'docname', fieldtype: 'Dynamic Link', label: 'Select Record', options: 'doctype', reqd: 1 }
            ],
            primary_action_label: 'Attach',
            primary_action: (values) => {
                frappe.call({
                    method: 'probuild.probuild.api.twilio.attach_conversation_to_record',
                    args: {
                        phone_number: phone_number,
                        target_doctype: values.doctype,
                        target_name: values.docname
                    },
                    callback: (r) => {
                        if (r.message?.success) {
                            frappe.show_alert({ message: r.message.message, indicator: 'green' });
                            d.hide();
                            this.load_conversations();
                        } else {
                            frappe.msgprint({ message: r.message?.message || 'Error', indicator: 'red' });
                        }
                    }
                });
            }
        });
        d.show();
    }

    refresh() {
        this.load_conversations();
        if (this.current_conversation) {
            this.load_conversation(this.current_conversation);
        }
    }
}
