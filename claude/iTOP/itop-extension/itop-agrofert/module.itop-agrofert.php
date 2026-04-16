<?php
/**
 * iTOP Extension: itop-agrofert
 *
 * Adds custom fields to UserRequest for importing tickets
 * from Agrofert Helpdesk (hd.agrofert.cz).
 */

SetupWebPage::AddModule(
    __FILE__,
    'itop-agrofert/1.0.0',
    [
        'label'        => 'Agrofert Helpdesk Integration',
        'category'     => 'business',
        'description'  => 'Custom fields on UserRequest for Agrofert HD import and reporting.',
        'dependencies' => [
            'itop-request-mgmt/2.7.0',
        ],
        'mandatory'    => false,
        'visible'      => true,
        'auto_select'  => false,
    ]
);
