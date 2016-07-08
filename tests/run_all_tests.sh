#!/bin/bash

for test in test*.py
do
  $1 $test
done
