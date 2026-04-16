<?php
/**
 * Czech dictionary for itop-agrofert extension.
 */
Dict::Add('CS CS', 'Czech', 'Čeština', [
    // UserRequest — Agrofert HD fields
    'Class:UserRequest/Attribute:external_id'        => 'AGF HD ID',
    'Class:UserRequest/Attribute:external_id+'       => 'ID tiketu v systému Agrofert Helpdesk (např. DC28073)',
    'Class:UserRequest/Attribute:subsidiary'         => 'Dceřiná společnost',
    'Class:UserRequest/Attribute:subsidiary+'        => 'Společnost v rámci skupiny Agrofert (např. AFEED, a.s.)',
    'Class:UserRequest/Attribute:agf_ticket_url'     => 'Odkaz AGF HD',
    'Class:UserRequest/Attribute:agf_ticket_url+'    => 'Přímý odkaz na tiket v portálu Agrofert Helpdesk',
    'Class:UserRequest/Attribute:agf_jira_id'        => 'JIRA ID',
    'Class:UserRequest/Attribute:agf_jira_id+'       => 'Navázaný tiket v systému JIRA',

    // WorkLog — general fields
    'Class:WorkLog/Attribute:work_location'             => 'Místo práce',
    'Class:WorkLog/Attribute:work_location+'            => 'Zda byla práce vykonána vzdáleně nebo přímo u zákazníka',
    'Class:WorkLog/Attribute:work_location/Value:remote'  => 'Remote',
    'Class:WorkLog/Attribute:work_location/Value:onsite'  => 'On-site',
    'Class:WorkLog/Attribute:kilometers'                => 'Kilometry',
    'Class:WorkLog/Attribute:kilometers+'               => 'Ujetá vzdálenost v km při výjezdu k zákazníkovi',
]);
