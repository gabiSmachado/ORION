#!/bin/bash

POLICY_ID=10002


curl -v -X PUT http://service-ricplt-a1mediator-http.ricplt.svc.cluster.local:10000/a1-p/policytypes/${POLICY_ID} \
-H "Content-Type: application/json" \
-d @policySchema.json