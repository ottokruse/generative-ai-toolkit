import json
import secrets
from generative_ai_toolkit.tracer.tracer import (
    StreamTracer,
    TeeTracer,
    traced,
    Trace,
    InMemoryTracer,
)
from generative_ai_toolkit.tracer.otlp import OtlpTracer
import time

tracer1 = TeeTracer()
tracer1.add_tracer(
    InMemoryTracer(trace_context_provider=tracer1),
)
# tracer1.add_tracer(StreamTracer(trace_context_provider=tracer1))
tracer1.add_tracer(OtlpTracer(trace_context_provider=tracer1))


tracer2 = TeeTracer()
tracer2.add_tracer(
    InMemoryTracer(trace_context_provider=tracer2),
)
# tracer2.add_tracer(StreamTracer(trace_context_provider=tracer2))
tracer2.add_tracer(OtlpTracer(trace_context_provider=tracer2))


conversation_id = secrets.token_hex(16)


tracer1.set_context(resource_attributes={"service.name": "city-agent"})
tracer2.set_context(resource_attributes={"service.name": "ticket-booking-agent"})


@traced("get-news", span_kind="CLIENT", tracer=tracer1)
def get_news():
    tracer1.current_trace.add_attribute("peer.service", "tool-get-news")
    tracer1.current_trace.add_attribute("payload", json.dumps({"city_name": "Munich"}))
    time.sleep(0.1)


@traced("get-weather", span_kind="CLIENT", tracer=tracer1)
def get_weather():
    tracer1.current_trace.add_attribute("peer.service", "tool-get-weather")
    tracer1.current_trace.add_attribute(
        "payload", json.dumps({"city_name": "Munich", "k": 5})
    )
    time.sleep(0.1)


@traced("invoke-ticket-agent", span_kind="CLIENT", tracer=tracer1)
def ticket_agent_ask_events():
    tracer1.current_trace.add_attribute("peer.service", "tool-ticket-agent")
    tracer1.current_trace.add_attribute(
        "payload", "What events are there in Munich this week?"
    )
    time.sleep(0.1)
    tracer2.set_context(
        span=Trace(
            "parent",
            trace_id=tracer1.current_trace.trace_id,
            span_id=tracer1.current_trace.span_id,
        ),
    )


@traced("invoke-ticket-agent", span_kind="CLIENT", tracer=tracer1)
def ticket_agent_book_event():
    tracer1.current_trace.add_attribute("peer.service", "tool-ticket-agent")
    tracer1.current_trace.add_attribute(
        "payload", "Buy me one ticket to Bruce Springsteen on Thursday, front row."
    )
    time.sleep(0.1)
    tracer2.set_context(
        span=Trace(
            "parent",
            trace_id=tracer1.current_trace.trace_id,
            span_id=tracer1.current_trace.span_id,
        ),
    )


@traced("invoke-ticket-agent", span_kind="CLIENT", tracer=tracer1)
def ticket_agent_confirm_booking():
    tracer1.current_trace.add_attribute("peer.service", "tool-ticket-agent")
    tracer1.current_trace.add_attribute(
        "payload", "Confirmed! Please go ahead and book"
    )
    time.sleep(0.1)
    tracer2.set_context(
        span=Trace(
            "parent",
            trace_id=tracer1.current_trace.trace_id,
            span_id=tracer1.current_trace.span_id,
        ),
    )


@traced("get-events", span_kind="CLIENT", tracer=tracer2)
def get_events():
    tracer2.current_trace.add_attribute("peer.service", "ticketmaster-api")
    tracer2.current_trace.add_attribute(
        "payload", json.dumps({"city_name": "Munich", "k": 10})
    )
    time.sleep(0.1)


@traced("create-booking", span_kind="CLIENT", tracer=tracer2)
def create_and_confirm_booking():
    tracer2.current_trace.add_attribute("peer.service", "ticketmaster-api")
    tracer2.current_trace.add_attribute(
        "payload", json.dumps({"event_id": "xyz", "ticket_type": "asd"})
    )
    time.sleep(0.1)


@traced("will-error", span_kind="CLIENT", tracer=tracer1)
def will_error():
    tracer1.current_trace.add_attribute("peer.service", "error-api")
    time.sleep(0.1)
    raise RuntimeError("This is an error")


with tracer1.trace("request", span_kind="SERVER") as span:
    span.add_attribute("conversation_id", conversation_id, inheritable=True)
    span.add_attribute("request", "Hi There! I'm going to Munich this week.")

    get_news()
    get_weather()
    ticket_agent_ask_events()
    try:
        will_error()
    except Exception:
        pass

    time.sleep(0.1)

    span.add_attribute(
        "response",
        "The weather in Munich will be ... The news headlines for Munich are ... Concerts this week are ...",
    )

with tracer2.trace("request", span_kind="SERVER") as span2:
    span2.add_attribute("conversation_id", conversation_id, inheritable=True)
    span2.add_attribute("request", "Hi There! I'm going to Munich this week.")
    get_events()
    time.sleep(0.1)
    span2.add_attribute("response", "Concerts this week in Munich are ...")

with tracer1.trace("request", span_kind="SERVER") as span3:
    span3.add_attribute("conversation_id", conversation_id, inheritable=True)
    span3.add_attribute(
        "request", "Cool. Book me the Bruce Springsteen concert on Tuesday please"
    )
    time.sleep(0.1)

    ticket_agent_book_event()
    span3.add_attribute(
        "response", "The price will be $100, please confirm you want to go ahead?"
    )

with tracer2.trace("request", span_kind="SERVER") as span4:
    span4.add_attribute("conversation_id", conversation_id, inheritable=True)
    span4.add_attribute(
        "request", "Create a booking for the Bruce Springsteen event on Tuesday"
    )
    span4.add_attribute(
        "response", "The price will be $100, please confirm you want to go ahead?"
    )
    time.sleep(0.1)

with tracer1.trace("request", span_kind="SERVER") as span5:
    span5.add_attribute("conversation_id", conversation_id, inheritable=True)
    span5.add_attribute("request", "Yes please go ahead")
    time.sleep(0.1)
    ticket_agent_confirm_booking()
    span5.add_attribute(
        "response",
        "Done; you are all set. Ticket has been emailed to you. Have fun in Munich.",
    )

with tracer2.trace("request", span_kind="SERVER") as span6:
    span6.add_attribute("conversation_id", conversation_id, inheritable=True)
    span6.add_attribute("request", "Confirmed")
    span6.add_attribute("response", "Ticket booked successfully")
    time.sleep(0.1)

traces1 = tracer1.get_traces()
traces2 = tracer2.get_traces()

print(len(traces1))
print(len(traces2))

for trace in [*traces1, *traces2]:
    print(
        trace.trace_id,
        trace.span_id,
        trace.span_name,
        " ".join(span.span_name for span in trace.parents),
    )
