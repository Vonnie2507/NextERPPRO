/**
 * SMS Notifications - Adds SMS badge to navbar
 */

frappe.provide('probuild.sms');

$(document).ready(function() {
    setTimeout(function() {
        probuild.sms.add_sms_badge();
        probuild.sms.setup_realtime_updates();
    }, 1000);
});

probuild.sms.add_sms_badge = function() {
    if ($('.probuild-sms-nav').length) return;
    
    const $navbar = $('.navbar-nav');
    if (!$navbar.length) return;
    
    const unread_count = frappe.boot.unread_sms_count || 0;
    
    const $sms_item = $(`
        <li class="nav-item dropdown probuild-sms-nav" title="SMS Messages">
            <a class="nav-link" href="/app/sms-conversations" style="position: relative; padding: 0.5rem 0.75rem;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity: 0.8;">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span class="probuild-sms-badge" style="
                    position: absolute;
                    top: 4px;
                    right: 2px;
                    background: #e74c3c;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    min-width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    display: ${unread_count > 0 ? 'flex' : 'none'};
                    align-items: center;
                    justify-content: center;
                    padding: 0 4px;
                ">${unread_count}</span>
            </a>
        </li>
    `);
    
    const $notif_bell = $navbar.find('.dropdown-notifications').parent();
    if ($notif_bell.length) {
        $sms_item.insertBefore($notif_bell);
    } else {
        $navbar.append($sms_item);
    }
};

probuild.sms.update_badge_count = function(count) {
    const $badge = $('.probuild-sms-badge');
    if ($badge.length) {
        $badge.text(count);
        if (count > 0) {
            $badge.show();
        } else {
            $badge.hide();
        }
    }
    frappe.boot.unread_sms_count = count;
};

probuild.sms.setup_realtime_updates = function() {
    frappe.realtime.on('new_sms', function(data) {
        probuild.sms.update_badge_count(data.new_count);
        
        frappe.show_alert({
            message: `<strong>New SMS from ${data.sender}</strong><br>${data.preview}`,
            indicator: 'blue'
        }, 10);
    });
    
    frappe.realtime.on('sms_unread_count_update', function(data) {
        probuild.sms.update_badge_count(data.new_count);
    });
};

probuild.sms.refresh_unread_count = function() {
    frappe.call({
        method: 'probuild.probuild.api.twilio.get_unread_sms_count',
        callback: function(r) {
            if (r.message !== undefined) {
                probuild.sms.update_badge_count(r.message);
            }
        }
    });
};
