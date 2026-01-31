"""Debug OpenAPI local_kw parameter"""
from app.main import app

# Find the POST /api/chat route
route = [r for r in app.routes if hasattr(r, 'path') and r.path == '/api/chat' and hasattr(r, 'methods') and 'POST' in r.methods][0]

print("=" * 60)
print("Route Analysis")
print("=" * 60)
print(f"Path: {route.path}")
print(f"Methods: {route.methods}")
print(f"Endpoint: {route.endpoint.__name__}")

dep = route.dependant
print(f"\nMain Dependant:")
print(f"  Query params: {dep.query_params}")
print(f"  Path params: {dep.path_params}")
print(f"  Body params: {[p.name for p in dep.body_params]}")

print(f"\nDependencies ({len(dep.dependencies)}):")
for i, d in enumerate(dep.dependencies):
    print(f"\n  Dependency {i}: {d.name}")
    print(f"    Call: {d.call}")
    print(f"    Query params: {d.query_params}")
    print(f"    Path params: {d.path_params}")
    
    if d.dependencies:
        print(f"    Sub-dependencies: {len(d.dependencies)}")
        for j, sd in enumerate(d.dependencies):
            print(f"      Sub-dep {j}: {sd.name}")
            print(f"        Query params: {sd.query_params}")
            print(f"        Path params: {sd.path_params}")

print("\n" + "=" * 60)
print("OpenAPI Schema Check")
print("=" * 60)

openapi_schema = app.openapi()
chat_post = openapi_schema['paths']['/api/chat']['post']
print(f"Parameters in OpenAPI schema:")
for param in chat_post.get('parameters', []):
    print(f"  - {param['name']} ({param['in']}): required={param.get('required', False)}")
