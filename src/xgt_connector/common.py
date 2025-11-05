#!/usr/bin/env python
# -*- coding: utf-8 -*- --------------------------------------------------===#
#
#  Copyright 2022-2025 Trovares Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===----------------------------------------------------------------------===#

import time
import datetime
import pyarrow.flight as pf

class BasicArrowClientAuthHandler(pf.ClientAuthHandler):
    def __init__(self):
        super().__init__()
        self.basic_auth = pf.BasicAuth()
        self.token = None
    def authenticate(self, outgoing, incoming):
        auth = self.basic_auth.serialize()
        outgoing.write(auth)
        self.token = incoming.read()
    def get_token(self):
        return self.token

class ProgressDisplay():
    def __init__(self, total_count, bar_size = 60, prefix = "Transferring: "):
        self._bar_end = '\r'
        # When drawing the bar, we can only use 1 line so we need to shrink
        # the bar elements for cases where the terminal is too tiny.
        try:
            terminal_size = os.get_terminal_size().columns
        except:
            # Can't get terminal_size
            terminal_size = 0
        static_element_size = 80
        current_space_requirement = static_element_size + bar_size
        # Can't get terminal_size
        if terminal_size == 0:
            pass
        # Terminal is too tiny for a bar: just print the results.
        elif terminal_size < static_element_size:
            bar_size = 0
            self._bar_end = '\n'
        # Shrink bar to fit the print within the terminal.
        elif terminal_size < current_space_requirement:
            bar_size = terminal_size - static_element_size
        self._total_count = total_count
        self._count = 0
        self._bar_size = bar_size
        self._prefix = prefix
        self._start_time = time.time()

    def __enter__(self):
        self.show_progress()
        return self

    def __exit__(self, exc_type,exc_value, exc_traceback):
        print("", flush=True)

    def __format_time(self, seconds, digits=1):
        isec, fsec = divmod(round(seconds*10**digits), 10**digits)
        return f'{datetime.timedelta(seconds=isec)}.{fsec:0{digits}.0f}'

    def show_progress(self, count_to_add = 0):
        self._count += count_to_add
        current_elapsed = time.time() - self._start_time
        rate = 0 if self._count == 0 else round(self._count / (current_elapsed), 1)
        duration = self.__format_time(current_elapsed)
        if self._total_count == 0:
            print("{}{} in {}s ({}/s)     ".format(self._prefix, self._count, duration, rate), end=self._bar_end, flush=True)
            return
        # Counts are no longer accurate
        while (self._count > self._total_count):
            self._total_count = self._count
        progress = int(self._count * self._bar_size / self._total_count)
        remaining = 0 if self._count == 0 else ((self._total_count - self._count) *
                                               (current_elapsed)) / self._count
        remaining = self.__format_time(remaining)
        print("{}[{}{}] {}/{} in {}s ({}/s, eta: {}s)     ".format(self._prefix,
              u"#"*progress, "."*(self._bar_size-progress), self._count,
              self._total_count, duration, rate, remaining), end=self._bar_end, flush=True)

