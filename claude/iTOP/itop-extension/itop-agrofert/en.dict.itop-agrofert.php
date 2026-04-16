<?php
/**
 * English dictionary for itop-agrofert extension.
 */
Dict::Add('EN US', 'English', 'English', [
    // UserRequest — Agrofert HD fields
    'Class:UserRequest/Attribute:external_id'        => 'AGF HD ID',
    'Class:UserRequest/Attribute:external_id+'       => 'Ticket ID in Agrofert Helpdesk system (e.g. DC28073)',
    'Class:UserRequest/Attribute:subsidiary'         => 'Subsidiary',
    'Class:UserRequest/Attribute:subsidiary+'        => 'Agrofert group subsidiary company (e.g. AFEED, a.s.)',
    'Class:UserRequest/Attribute:agf_ticket_url'     => 'AGF HD Link',
    'Class:UserRequest/Attribute:agf_ticket_url+'    => 'Direct link to the ticket in Agrofert Helpdesk portal',
    'Class:UserRequest/Attribute:agf_jira_id'        => 'JIRA ID',
    'Class:UserRequest/Attribute:agf_jira_id+'       => 'Linked ticket in JIRA',

    // WorkLog — general fields
    'Class:WorkLog/Attribute:work_location'             => 'Work location',
    'Class:WorkLog/Attribute:work_location+'            => 'Whether the work was performed remotely or on-site at the customer',
    'Class:WorkLog/Attribute:work_location/Value:remote'  => 'Remote',
    'Class:WorkLog/Attribute:work_location/Value:onsite'  => 'On-site',
    'Class:WorkLog/Attribute:kilometers'                => 'Kilometers',
    'Class:WorkLog/Attribute:kilometers+'               => 'Travel distance in km for on-site visits',
]);
